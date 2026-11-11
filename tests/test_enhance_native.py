import asyncio
from pathlib import Path
import tempfile
import unittest
from sprite_studio.features.enhance import service
from sprite_studio.runtime.jobs import JobCoordinator
from sprite_studio.storage import StudioStore
from sprite_studio.features.gallery.service import Gallery

class NativeEnhanceTests(unittest.TestCase):
    def test_native_graph_and_constraints(self):
        draft={'kind':'turnaround','prompt':'A copper robot','references':[{'note':'red LEFT arm','enabled':True}], 'turnaround':{'locks':'two antennas'}}
        recipe=service.enhance_recipe({'draft':draft})
        graph=service.build_enhance_graph(recipe)
        self.assertEqual(graph['700']['class_type'],'CLIPLoader')
        self.assertEqual(graph['700']['inputs']['device'],'default')
        self.assertEqual(graph['702']['class_type'],'TextGenerateV2')
        self.assertIn('red LEFT arm',graph['702']['inputs']['prompt'])
        self.assertIn('two antennas',graph['702']['inputs']['prompt'])
        self.assertIn('Do not add scenery',graph['701']['inputs']['value'])
        self.assertEqual(draft['prompt'],'A copper robot')
        self.assertEqual(service.build_enhance_graph(recipe,cpu=True)['700']['inputs']['device'],'cpu')

    def test_only_enhance_model_required(self):
        from sprite_studio.runtime.models import required_files
        self.assertEqual([s['path'] for s in required_files({'kind':'enhance'})],['text_encoders/'+service.MODEL_NAME])

    def test_resource_failures_only(self):
        self.assertTrue(service.gpu_resource_error('CUDA out of memory'))
        for error in ('Invalid prompt','File not found','CPU out of memory'):
            self.assertFalse(service.gpu_resource_error(error))

class NativeEnhanceJobsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=StudioStore(Path(self.temp.name));self.addCleanup(self.store.close)
        class Engine:
            async def queue(self):return {'queue_running':[],'queue_pending':[]}
            async def history(self,prompt_id):return None
            async def submit(self,graph,client,workflow,prompt_id):return prompt_id
            async def cancel(self,prompt_id):raise AssertionError('No queued job should be canceled')
        self.jobs=JobCoordinator(self.store,Engine(),lambda *args:None)
        self.addAsyncCleanup(self.jobs.close)

    async def prepared(self):
        run=await self.jobs.submit({'kind':'enhance','draft':{'kind':'create_image','prompt':'A copper robot'}},'enhance','client')
        await self.jobs.tasks[run['id']]
        run=self.store.get_run(run['id']);self.assertEqual(run['status'],'ready')
        return run

    def error(self,message):return {'status':{'status_str':'error','messages':[['execution_error',{'exception_message':message}]]},'outputs':{}}

    async def retry(self):
        run=await self.prepared()
        self.store.update_run(run['id'],'running',run['detail'],'gpu-id')
        await self.jobs._finish(self.store.get_run(run['id']),self.error('CUDA out of memory'))
        return self.store.get_run(run['id'])

    async def test_gpu_failure_prepares_one_visible_cpu_retry(self):
        run=await self.retry()
        self.assertEqual(run['status'],'ready');self.assertIsNone(run['prompt_id'])
        self.assertEqual(run['detail']['graph']['700']['inputs']['device'],'cpu')
        await self.jobs.start(run['id'],{'extra':{'sprite_studio':{'schema':1}}})
        self.assertNotEqual(self.store.get_run(run['id'])['prompt_id'],'gpu-id')
        self.jobs.tasks[run['id']].cancel()
        await self.jobs._finish(self.store.get_run(run['id']),self.error('CPU out of memory'))
        self.assertEqual(self.store.get_run(run['id'])['status'],'failed')

    async def test_text_success_reports_device_and_skips_gallery(self):
        run=await self.prepared()
        await self.jobs._finish(run,{'status':{'status_str':'success'},'outputs':{'703':{'text':['{"prompt":"A copper robot."}'],'device':['cuda:0']}}})
        result=self.store.get_run(run['id'])
        self.assertEqual(result['status'],'completed');self.assertEqual(result['detail']['device'],'GPU')
        self.assertEqual(result['detail']['candidate'],'A copper robot.')
        self.assertEqual(Gallery(self.store).list()['runs'],[])

    async def test_bad_content_does_not_retry(self):
        run=await self.prepared()
        await self.jobs._finish(run,{'status':{'status_str':'success'},'outputs':{'703':{'text':['not JSON'],'device':['cuda:0']}}})
        self.assertEqual(self.store.get_run(run['id'])['status'],'failed')

    async def test_cancel_pending_retry_does_not_cancel_old_gpu_job(self):
        run=await self.retry()
        self.assertEqual((await self.jobs.cancel(run['id']))['status'],'canceled')

    async def test_restart_does_not_replay_previous_failure(self):
        run=await self.retry();await self.jobs.recover()
        self.assertEqual(self.store.get_run(run['id'])['status'],'interrupted')

    async def test_duplicate_gpu_completion_cannot_overwrite_pending_cpu_attempt(self):
        run=await self.prepared()
        self.store.update_run(run['id'],'running',run['detail'],'gpu-id')
        old=self.store.get_run(run['id'])
        await asyncio.gather(self.jobs._finish(old,self.error('CUDA out of memory')),self.jobs._finish(old,self.error('CUDA out of memory')))
        self.assertEqual(self.store.get_run(run['id'])['status'],'ready')
