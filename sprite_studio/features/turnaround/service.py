"""Own reviewed exports of completed Studio sheets."""
from pathlib import Path
import json
import re
import shutil
import uuid
import zipfile
from PIL import Image
from ...storage import safe_path
from ...runtime.temporary import TemporaryFiles
from ..references.model import active_cards
from .crops import default_crops, export_images


class TurnaroundExports:
    def __init__(self,store,output_root,temporary=None):
        self.store=store
        self.output_root=Path(output_root).resolve()
        self.temporary=temporary or TemporaryFiles(store.path('temporary'))

    def source(self,run_id):
        run=self.store.get_run(run_id)
        if not run or run['status']!='completed': raise ValueError('Choose a completed Sprite Studio image.')
        outputs=run['detail'].get('outputs',[])
        if not outputs: raise ValueError('The result image is unavailable.')
        output=outputs[0]
        subfolder=str(output.get('subfolder','')).replace('\\','/')
        if subfolder!=f'sprite_studio/{run_id}' or Path(output['filename']).name!=output['filename']:
            raise ValueError('The result is outside this Studio job.')
        path=safe_path(self.output_root,subfolder+'/'+output['filename'])
        if not path.is_file(): raise ValueError('The saved master image is missing.')
        return run,path

    def review(self,run_id):
        run,path=self.source(run_id)
        if run['recipe']['kind']!='turnaround': raise ValueError('Choose a completed turnaround sheet.')
        with Image.open(path) as image: size=list(image.size)
        config=run['recipe']['turnaround']
        prior=self.store.get_document('crop_reviews',run_id,{})
        return {'run_id':run_id,'image':run['detail']['outputs'][0],'size':size,'views':config['views'],
                'download':f'/sprite-studio/v1/export-file?id={prior["export_id"]}' if prior.get('export_id') else None,
                'rectangles':prior.get('rectangles',default_crops(*size,len(config['views']),config['columns']))}

    def export(self,run_id,rectangles,reviewed):
        if reviewed is not True: raise ValueError('Inspect the views and confirm their identity and orientation before export.')
        run,path=self.source(run_id)
        if run['recipe']['kind']!='turnaround': raise ValueError('Choose a turnaround result.')
        config=run['recipe']['turnaround']
        export_id=uuid.uuid4().hex
        archive=self.store.path(f'exports/{export_id}.zip')
        archive.parent.mkdir(parents=True,exist_ok=True)
        # Work stays leased until a complete archive is atomically promoted on
        # the same filesystem. Interrupted scratch is safe for Cache Purge.
        with self.temporary.lease() as scratch:
            directory=scratch/'views'
            manifest=export_images(path,directory,rectangles,config['views'],{k:config[k] for k in ('projection','elevation','fov')})
            manifest.update({'run_id':run_id,'recipe':run['recipe'],'master_file':'master.png',
                             'actual_prompt':run['detail'].get('actual_prompt',run['detail'].get('compiled_prompt','')),
                             'reference_mapping':[{'picture':i,**card} for i,card in enumerate(active_cards(run['recipe']),1)]})
            shutil.copyfile(path,directory/'master.png')
            (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            staging=scratch/'views.zip'
            with zipfile.ZipFile(staging,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
                for child in sorted(directory.iterdir()): bundle.write(child,child.name)
            staging.replace(archive)
            for child in directory.iterdir(): child.unlink()
            directory.rmdir()
        self.store.put_document('exports',export_id,{'run_id':run_id,'storage':'studio','path':f'exports/{export_id}.zip','manifest':manifest})
        self.store.put_document('crop_reviews',run_id,{'rectangles':rectangles,'reviewed':True,'export_id':export_id})
        return {'id':export_id,'manifest':manifest,'download':f'/sprite-studio/v1/export-file?id={export_id}'}

    def file(self,export_id):
        if not re.fullmatch('[0-9a-f]{32}',str(export_id)): raise ValueError('Choose a saved export.')
        record=self.store.get_document('exports',export_id)
        if not record: raise ValueError('Export is unavailable.')
        return self.store.path(record['path']) if record.get('storage')=='studio' else safe_path(self.output_root,record['path'])

    def to_library(self,run_id,rectangles,reviewed,name,references,library):
        exported=self.export(run_id,rectangles,reviewed)
        cards=[]
        with zipfile.ZipFile(self.file(exported['id'])) as bundle:
            for index,view in enumerate(exported['manifest']['views']):
                asset=references.import_image(bundle.read(view['file']),view['file'])
                cards.append({'asset_id':asset['id'],'role':'identity' if index==0 else 'construction',
                    'note':f"{view['label']} view of the same subject. Requested camera azimuth {view['azimuth']} degrees; preserve the visible construction and side-specific details.",'enabled':True})
        return library.save({'name':name,'references':cards,'notes':'Reviewed turnaround views. Keep the same identity, construction, pose and rendering style.',
                             'category':'identity','tags':'turnaround, reviewed'})
