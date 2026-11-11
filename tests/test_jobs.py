import asyncio
import importlib
from pathlib import Path
import tempfile
import threading
import unittest
from sprite_studio.storage import StudioStore


class EngineBoundary:
    def __init__(self):
        self.submitted=[]
        self.canceled=[]
        self.result=None
    async def submit(self, graph, client_id, workflow, prompt_id=None):
        self.submitted.append(graph)
        return prompt_id or '12345678-1234-1234-1234-123456789abc'
    async def history(self, prompt_id): return self.result
    async def cancel(self, prompt_id): self.canceled.append(prompt_id)
    async def queue(self):return {'queue_running':[],'queue_pending':[]}


class JobsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        try:
            module=importlib.import_module('sprite_studio.runtime.jobs')
        except ModuleNotFoundError:
            self.fail('Owned job coordinator is not implemented')
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=StudioStore(Path(self.temp.name))
        self.addCleanup(self.store.close)
        self.engine=EngineBoundary()
        self.calls=[]
        def ensure(recipe,progress,cancel): self.calls.append(recipe['profile'])
        self.jobs=module.JobCoordinator(self.store,self.engine,ensure)
        self.addAsyncCleanup(self.jobs.close)

    async def ready(self, job):
        for _ in range(20):
            await asyncio.sleep(.01)
            result=self.store.get_run(job['id'])
            if result['status']=='ready': return result
        self.fail('Prepared job did not become ready')

    async def test_prepare_is_idempotent_and_waits_for_live_graph_ack(self):
        first=await self.jobs.submit({'prompt':'A red shuttle'},'click-one','client')
        second=await self.jobs.submit({'prompt':'A red shuttle'},'click-one','client')
        self.assertEqual(first['id'],second['id'])
        job=await self.ready(first)
        self.assertEqual(self.calls,['w4a8'])
        self.assertEqual(self.engine.submitted,[])
        await self.jobs.start(job['id'],{'extra':{'sprite_studio':{'schema':1}}})
        await self.jobs.start(job['id'],{'extra':{'sprite_studio':{'schema':1}}})
        self.assertEqual(len(self.engine.submitted),1)

    async def test_cancel_before_execution_never_interrupts_comfy(self):
        first=await self.jobs.submit({'prompt':'A red shuttle'},'click-two','client')
        await self.ready(first)
        await self.jobs.cancel(first['id'])
        self.assertEqual(self.engine.canceled,[])
        self.assertEqual(self.store.get_run(first['id'])['status'],'canceled')

    async def test_cancellation_targets_only_owned_prompt(self):
        first=await self.jobs.submit({'prompt':'A red shuttle'},'click-three','client')
        await self.ready(first)
        await self.jobs.start(first['id'],{'extra':{'sprite_studio':{'schema':1}}})
        await self.jobs.cancel(first['id'])
        import uuid
        self.assertEqual(self.engine.canceled,[str(uuid.UUID(first['id']))])
        with self.assertRaises(ValueError): await self.jobs.cancel('f'*32)

    async def test_restart_reconciles_completed_output_without_resubmitting(self):
        recipe={'kind':'create_image','prompt':'Robot','profile':'w4a8'}
        self.store.create_run('b'*32,recipe,'before-restart')
        self.store.update_run('b'*32,'queued',{'compiled_prompt':'Robot','started':1},'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        self.engine.result={'status':{'status_str':'success'},'outputs':{'112':{'images':[{'filename':'robot.png','type':'output'}]}}}
        await self.jobs.recover()
        result=self.store.get_run('b'*32)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['detail']['outputs'][0]['filename'],'robot.png')
        self.assertEqual(self.engine.submitted,[])

    async def test_restart_preserves_interrupted_download_recipe(self):
        self.store.create_run('c'*32,{'prompt':'Robot','kind':'create_image'},'download-before-restart')
        self.store.update_run('c'*32,'downloading',{'bytes':100,'total':200})
        await self.jobs.recover()
        result=self.store.get_run('c'*32)
        self.assertEqual(result['status'],'interrupted')
        self.assertEqual(result['recipe']['prompt'],'Robot')
        self.assertIn('resume',result['detail']['message'].lower())

    async def test_completion_between_history_and_queue_reads_is_preserved(self):
        run_id='d'*32
        self.store.create_run(run_id,{'kind':'create_image','prompt':'Robot'},'finish-race')
        self.store.update_run(run_id,'running',{'compiled_prompt':'Robot'},'native-id')
        async def finished_queue():
            self.engine.result={'status':{'status_str':'success'},'outputs':{'112':{'images':[{'filename':'robot.png','type':'output'}]}}}
            return {'queue_running':[],'queue_pending':[]}
        self.engine.queue=finished_queue
        await self.jobs._monitor(run_id,'native-id')
        self.assertEqual(self.store.get_run(run_id)['status'],'completed')

    async def test_concurrent_completion_registers_refmod_once(self):
        run_id='e'*32
        self.store.create_run(run_id,{'kind':'refmod','prompt':'Robot'},'refmod-finish-race')
        self.store.update_run(run_id,'running',{},'native-id')
        calls=[]
        class Refmods:
            def complete(self,run,outputs):
                import time
                calls.append(run['id']);time.sleep(.03)
                return {'id':run['id']}
        self.jobs.refmods=Refmods()
        history={'status':{'status_str':'success'},'outputs':{'590':{'images':[{'filename':'robot.png','type':'output'}]}}}
        run=self.store.get_run(run_id)
        await asyncio.gather(self.jobs._finish(run,history),self.jobs._finish(run,history))
        self.assertEqual(calls,[run_id])

    async def test_cancel_does_not_overwrite_concurrent_completed_result(self):
        run_id='f'*32
        self.store.create_run(run_id,{'kind':'create_image','prompt':'Robot'},'cancel-finish-race')
        self.store.update_run(run_id,'running',{},'native-id')
        async def cancel_after_completion(prompt_id):
            self.store.update_run(run_id,'completed',{'outputs':[{'filename':'robot.png','type':'output'}]})
        self.engine.cancel=cancel_after_completion
        result=await self.jobs.cancel(run_id)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['detail']['outputs'][0]['filename'],'robot.png')
