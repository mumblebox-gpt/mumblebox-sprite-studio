"""Composition root; each feature owns its behavior behind this wiring."""
from pathlib import Path
import time
from .storage import StudioStore
from .runtime.comfy import ComfyClient
from .runtime.models import ModelDownloads
from .runtime.jobs import JobCoordinator
from .features.references.service import ReferenceAssets
from .features.create_image.schema import FIELDS
from .features.references.model import ROLES
from .features.turnaround.schema import FIELDS as TURNAROUND_FIELDS, validate_turnaround
from .features.turnaround.service import TurnaroundExports
from .features.enhance.service import MODEL_NAME
from .features.gallery.service import Gallery
from .runtime.temporary import TemporaryFiles
from .features.refmods.service import RefModLibrary
from .features.refmods.schema import FIELDS as REFMOD_FIELDS
from .features.settings.service import Settings

VERSION='0.1.0-dev.4'


class StudioApplication:
    def __init__(self, folders, port):
        self.folders = folders
        self.store = StudioStore(Path(folders.get_user_directory())/'mumblebox_sprite_studio')
        self.settings=Settings(self.store)
        self.engine = ComfyClient(port)
        self.models = ModelDownloads(self.store,folders.models_dir,folders.get_full_path)
        self.references = ReferenceAssets(self.store,folders.get_input_directory())
        self.temporary = TemporaryFiles(self.store.path('temporary'))
        self.exports = TurnaroundExports(self.store,folders.get_output_directory(),self.temporary)
        self.gallery = Gallery(self.store)
        try:mod_roots=folders.get_folder_paths('refmods')
        except KeyError:mod_roots=[]
        self.refmods=RefModLibrary(self.store,self.references,mod_roots[0] if mod_roots else Path(folders.models_dir)/'refmods',folders.get_output_directory())
        self.jobs = JobCoordinator(self.store,self.engine,self.models.ensure,self.refmods)
        self.stats = None
        self.stats_at = 0

    def bootstrap(self):
        defaults = {key:field['default'] for key,field in FIELDS.items()}
        defaults.update({'prompt':'','references':[],'kind':'create_image'})
        drafts = {kind:self.store.get_document('drafts',kind,{**defaults,'kind':kind}) for kind in ('create_image','turnaround')}
        if 'turnaround' not in drafts['turnaround']:
            drafts['turnaround'].update({'turnaround':validate_turnaround({}),'width':4096,'height':1024})
        drafts['refmod']=self.store.get_document('drafts','refmod',{'kind':'refmod','prompt':'','references':[],'notes':'','tags':'','refmod':{key:field['default'] for key,field in REFMOD_FIELDS.items()}})
        return {'version':VERSION,'fields':FIELDS,'roles':ROLES,'drafts':drafts,
                'turnaround_fields':TURNAROUND_FIELDS,
                'refmod_fields':REFMOD_FIELDS,
                'enhancer':{'available':True,'model':MODEL_NAME,'preferred_device':'GPU'},
                'latest':{kind:self.store.latest_completed(kind) for kind in ('create_image','turnaround')},
                'settings':self.settings.get(),
                'models':self.models.inventory(),'active_id':self.jobs.active_id}

    async def telemetry(self):
        if time.monotonic()-self.stats_at<2 and self.stats:
            return self.stats
        import psutil
        import comfy.model_management
        stats = await self.engine.request('GET','/system_stats')
        queue = await self.engine.request('GET','/queue')
        self.stats = {'cpu':psutil.cpu_percent(), 'ram':dict(psutil.virtual_memory()._asdict()),
                      'devices':stats.get('devices',[]),'loaded_models':len(comfy.model_management.current_loaded_models),
                      'queue':{'running':len(queue['queue_running']),'pending':len(queue['queue_pending'])}}
        self.stats_at = time.monotonic()
        return self.stats
