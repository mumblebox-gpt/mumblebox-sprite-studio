"""Own a run from download through live-graph acknowledgment and completion."""
import asyncio
import re
import threading
import time
import uuid
from ..features.create_image.schema import validate_recipe, freeze_seed
from ..features.create_image.workflow import build_prompt_graph
from ..features.create_image.prompt import build_prompt
from ..features.references.model import active_cards
from ..features.enhance.service import enhance_recipe, build_enhance_graph, completion as enhance_completion

TERMINAL = {'completed','failed','canceled','interrupted'}


class JobCoordinator:
    def __init__(self, store, engine, ensure_models, refmods=None):
        self.store = store
        self.engine = engine
        self.ensure_models = ensure_models
        self.refmods = refmods
        self.lock = asyncio.Lock()
        self.active_id = None
        self.tasks = {}
        self.cancels = {}
        self.clients = {}
        self.recovered = False
        self.recovery_lock = asyncio.Lock()
        self.finish_lock = asyncio.Lock()

    def owned(self,run_id):return self._owned(run_id)

    @staticmethod
    def _queued_ids(queue):
        return {row[1] for key in ('queue_running','queue_pending') for row in queue.get(key,[])}

    async def recover(self):
        """Reconcile durable requests once; never resubmit an uncertain job."""
        async with self.recovery_lock:
            if self.recovered:return
            runs=self.store.unfinished_runs()
            queue=await self.engine.queue() if any(run['prompt_id'] for run in runs) else {}
            queued=self._queued_ids(queue)
            for run in runs:
                prompt_id=run['prompt_id']
                history=await self.engine.history(prompt_id) if prompt_id else None
                if history:
                    await self._finish(run,history)
                elif prompt_id and prompt_id in queued:
                    self.active_id=run['id']
                    self.store.update_run(run['id'],'queued',{**run['detail'],'message':'Reconnected to the existing ComfyUI job.'})
                    self.tasks[run['id']]=asyncio.create_task(self._monitor(run['id'],prompt_id))
                else:
                    self.store.update_run(run['id'],'interrupted',{**run['detail'],'message':'The previous session stopped. Reuse this recipe to retry; partial model downloads resume automatically.'})
            self.recovered=True

    def _owned(self, run_id):
        if not re.fullmatch('[0-9a-f]{32}',str(run_id)):
            raise ValueError('Select a Sprite Studio job.')
        run = self.store.get_run(run_id)
        if run is None:
            raise ValueError('This is not a Sprite Studio job.')
        return run

    async def submit(self, data, request_id, client_id):
        if not isinstance(request_id,str) or not 1<=len(request_id)<=100:
            raise ValueError('Generation request needs a stable request ID.')
        async with self.lock:
            existing = self.store.by_request(request_id)
            if existing:
                return existing
            if self.active_id and self._owned(self.active_id)['status'] not in TERMINAL:
                raise ValueError('Finish or cancel the current Sprite Studio job first.')
            if isinstance(data,dict) and data.get('kind')=='enhance':recipe=enhance_recipe(data)
            else:recipe = self.refmods.recipe(data) if self.refmods and isinstance(data,dict) and data.get('kind')=='refmod' else freeze_seed(validate_recipe(data))
            files = [self.store.get_asset(card['asset_id'])['filename'] for card in active_cards(recipe)]
            run_id = uuid.uuid4().hex
            self.store.create_run(run_id,recipe,request_id)
            self.active_id = run_id
            self.cancels[run_id] = threading.Event()
            self.clients[run_id] = str(client_id)[:128]
            for old_id,task in list(self.tasks.items()):
                if task.done():
                    self.tasks.pop(old_id,None);self.cancels.pop(old_id,None);self.clients.pop(old_id,None)
            self.tasks[run_id] = asyncio.create_task(self._prepare(run_id,files))
            return self._owned(run_id)

    async def _prepare(self, run_id, files):
        cancel = self.cancels[run_id]
        recipe = self._owned(run_id)['recipe']
        last_update = 0.0
        def progress(detail):
            nonlocal last_update
            now = time.monotonic()
            if not cancel.is_set() and (now-last_update>=.4 or detail['stage'] in ('fallback','ready')):
                self.store.update_run(run_id,'downloading',detail)
                last_update = now
        try:
            await asyncio.to_thread(self.ensure_models,recipe,progress,cancel)
            if cancel.is_set():
                return
            is_refmod=recipe['kind']=='refmod'
            is_enhance=recipe['kind']=='enhance'
            graph = build_enhance_graph(recipe) if is_enhance else self.refmods.graph(recipe,files,run_id) if is_refmod else build_prompt_graph(recipe,files,run_id)
            self.store.update_run(run_id,'ready',{'graph':graph,'compiled_prompt':recipe['prompt'] if is_refmod or is_enhance else build_prompt(recipe),
                'message':'Models ready. Connecting the visible workflow.'})
        except InterruptedError:
            self.store.update_run(run_id,'canceled',{'message':'Canceled. Partial model downloads can resume on your next run.'})
        except Exception as error:
            self.store.update_run(run_id,'failed',{'message':str(error)})

    async def start(self, run_id, workflow):
        async with self.lock:
            run = self._owned(run_id)
            if run['status'] in ('submitting','queued','running','recovering','canceling') or run['status'] in TERMINAL:
                return run
            if run['status']!='ready':
                raise ValueError('Models are not ready yet.')
            if not isinstance(workflow,dict) or not workflow.get('extra',{}).get('sprite_studio'):
                raise ValueError('Open the Sprite Studio graph before starting generation.')
            try:
                prompt_id=str(uuid.uuid5(uuid.UUID(run_id),'cpu-fallback')) if run['detail'].get('cpu_fallback') else str(uuid.UUID(run_id))
                self.store.update_run(run_id,'submitting',{**run['detail'],'started':time.time(),'message':'Submitting the visible workflow.'},prompt_id)
                returned_id = await self.engine.submit(run['detail']['graph'],self.clients.get(run_id,''),workflow,prompt_id)
                if returned_id!=prompt_id:raise ValueError('ComfyUI returned an unexpected job identity.')
                self.store.update_run(run_id,'queued',{**run['detail'],'compiled_prompt':run['detail']['compiled_prompt'],
                    'started':time.time(),'message':'Queued in ComfyUI.'},prompt_id)
                self.tasks[run_id] = asyncio.create_task(self._monitor(run_id,prompt_id))
            except ValueError as error:
                self.store.update_run(run_id,'failed',{'message':str(error)})
            except Exception as error:
                self.store.update_run(run_id,'recovering',{**self._owned(run_id)['detail'],'message':f'Checking whether ComfyUI accepted the request: {error}'})
                self.tasks[run_id]=asyncio.create_task(self._monitor(run_id,prompt_id))
            return self._owned(run_id)

    async def _finish(self,run,history):
        async with self.finish_lock:
            current=self._owned(run['id'])
            if current['status'] in TERMINAL:return
            if current['prompt_id']!=run['prompt_id']:return
            await self._record_completion(current,history)

    async def _record_completion(self,run,history):
        if run['recipe']['kind']=='enhance':
            state,detail=enhance_completion(run,history)
            detail['seconds']=round(time.time()-detail.get('started',time.time()),1)
            self.store.update_run(run['id'],state,detail,clear_prompt=state=='ready')
            return
        status=history.get('status',{})
        outputs=[image for node in history.get('outputs',{}).values() for image in node.get('images',[]) if image.get('type')=='output']
        detail={**run['detail'],'seconds':time.time()-run['detail'].get('started',time.time()),'outputs':outputs}
        prompt_node='142' if run['recipe']['kind']=='create_image' else '342'
        helper_text=history.get('outputs',{}).get(prompt_node,{}).get('text',[])
        detail['actual_prompt']=helper_text[0] if helper_text else run['detail'].get('compiled_prompt','')
        if status.get('status_str')=='success' and outputs:
            if run['recipe']['kind']=='refmod':
                try:detail['library_item']=await asyncio.to_thread(self.refmods.complete,run,outputs)
                except Exception as error:
                    detail['message']=f'ComfyUI finished, but the RefMod could not be registered: {error}. Generated files were preserved.'
                    self.store.update_run(run['id'],'failed',detail)
                    return
            detail['message']='References saved in the RefMods library.' if run['recipe']['kind']=='refmod' else 'Image saved to Gallery.'
            self.store.update_run(run['id'],'completed',detail)
        else:
            canceled=run['detail'].get('cancel_requested',False)
            messages=status.get('messages',[])
            detail['message']='Canceled. Your recipe and references are saved.' if canceled else next((item[1].get('exception_message','') for item in messages if item[0]=='execution_error'),'Generation did not finish. Retry with the saved settings.')
            self.store.update_run(run['id'],'canceled' if canceled else 'failed',detail)

    async def _monitor(self, run_id, prompt_id):
        failures=0
        while True:
            try:
                run = self._owned(run_id)
                if run['status'] in TERMINAL:
                    return
                history = await self.engine.history(prompt_id)
                if history:
                    await self._finish(run,history)
                    return
                queue=await self.engine.queue()
                if prompt_id not in self._queued_ids(queue):
                    # Completion can land between the history and queue reads.
                    history=await self.engine.history(prompt_id)
                    if history:
                        await self._finish(run,history)
                        return
                    run=self._owned(run_id)
                    if run['status'] in TERMINAL:return
                    if run['detail'].get('cancel_requested'):
                        self.store.update_run(run_id,'canceled',{**run['detail'],'message':'Canceled. Your recipe and references are saved.'})
                    else:self.store.update_run(run_id,'interrupted',{**run['detail'],'message':'ComfyUI no longer has this request. Reuse the saved recipe to retry.'})
                    return
                if run['status']!='canceling':
                    running=prompt_id in {row[1] for row in queue.get('queue_running',[])}
                    state='running' if running else 'queued'
                    if run['status']!=state:self.store.update_run(run_id,state,{**run['detail'],'message':'Generating in ComfyUI…' if running else 'Waiting in the ComfyUI queue.'})
                failures=0
                await asyncio.sleep(1)
            except asyncio.CancelledError:raise
            except Exception as error:
                failures+=1
                run=self._owned(run_id)
                self.store.update_run(run_id,'recovering',{**run['detail'],'message':f'Reconnecting to the existing job: {error}. Your recipe is saved.'})
                await asyncio.sleep(min(10,failures*2))

    async def cancel(self, run_id):
        async with self.lock:
            run = self._owned(run_id)
            if run['status'] in TERMINAL:
                return run
            self.cancels.setdefault(run_id,threading.Event()).set()
            if run['prompt_id']:
                history=await self.engine.history(run['prompt_id'])
                if history:
                    await self._finish(run,history)
                    return self._owned(run_id)
                await self.engine.cancel(run['prompt_id'])
                run=self._owned(run_id)
                if run['status'] in TERMINAL:return run
                detail={**run['detail'],'cancel_requested':True,'message':'Canceling this Studio job…'}
                self.store.update_run(run_id,'canceling',detail)
                history=await self.engine.history(run['prompt_id'])
                if history:await self._finish(self._owned(run_id),history)
                elif run['prompt_id'] not in self._queued_ids(await self.engine.queue()):self.store.update_run(run_id,'canceled',{**detail,'message':'Canceled. Your recipe and references are saved.'})
                return self._owned(run_id)
            self.store.update_run(run_id,'canceled',{'message':'Canceled. Your recipe and references are saved.'})
            return self._owned(run_id)

    async def close(self):
        for cancel in self.cancels.values():
            cancel.set()
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(),return_exceptions=True)
