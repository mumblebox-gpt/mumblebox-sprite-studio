"""Own collections and actual RefMod files, originals and copy-on-use selection."""
from io import BytesIO
import json
from pathlib import Path
import re
import time
import uuid
import zipfile
from ...storage import safe_path
from ..references.model import validate_cards, active_cards
from .format import inspect_bytes, MAX_FILE
from .schema import validate
from .workflow import build_graph


class RefModLibrary:
    def __init__(self,store,references,mod_root,output_root):
        self.store=store;self.references=references
        self.mod_root=Path(mod_root).resolve();self.output_root=Path(output_root).resolve()
        with store.lock,store.db:
            store.db.execute('CREATE TABLE IF NOT EXISTS ref_library(id TEXT PRIMARY KEY,updated REAL NOT NULL,trashed INTEGER NOT NULL DEFAULT 0,data TEXT NOT NULL)')
            store.db.execute('CREATE INDEX IF NOT EXISTS ref_library_list ON ref_library(trashed,updated DESC,id)')

    @staticmethod
    def identifier(value):
        if not re.fullmatch('[0-9a-f]{32}',str(value)):raise ValueError('Choose a saved RefMods entry.')
        return value

    def get(self,ident):
        self.identifier(ident)
        with self.store.lock:row=self.store.db.execute('SELECT data FROM ref_library WHERE id=?',(ident,)).fetchone()
        if not row:raise ValueError('This RefMods entry is unavailable.')
        return json.loads(row[0])

    def list(self,offset=0,trashed=False):
        if type(offset) is not int or not 0<=offset<=100000:raise ValueError('Invalid library page.')
        with self.store.lock:rows=self.store.db.execute('SELECT data FROM ref_library WHERE trashed=? ORDER BY updated DESC,id LIMIT 51 OFFSET ?',(int(trashed),offset)).fetchall()
        return {'items':[json.loads(row[0]) for row in rows[:50]],'has_more':len(rows)>50}

    def _write(self,item):
        item={**item,'updated':time.time()}
        with self.store.lock,self.store.db:
            self.store.db.execute('INSERT INTO ref_library VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,trashed=excluded.trashed,data=excluded.data',
                (item['id'],item['updated'],int(item.get('trashed',False)),json.dumps(item,ensure_ascii=False,allow_nan=False)))
        return item

    def save(self,data):
        if not isinstance(data,dict):raise ValueError('Provide reference collection details.')
        prior=self.get(data['id']) if data.get('id') else {'id':uuid.uuid4().hex,'kind':'collection','references':[],'member_count':0,'trashed':False}
        name=str(data.get('name',prior.get('name',''))).strip()
        if not 1<=len(name)<=160:raise ValueError('Give the collection a name of up to 160 characters.')
        cards=validate_cards(data.get('references',prior['references']))
        if prior['kind']=='refmod' and [c['asset_id'] for c in cards]!=[c['asset_id'] for c in prior['references']]:
            raise ValueError('Use Save as new collection when replacing an encoded RefMod’s original pictures.')
        if len(cards)>8:raise ValueError('Save up to eight pictures per collection.')
        for card in cards:self.store.get_asset(card['asset_id'])
        category=str(data.get('category',prior.get('category','identity')))
        if category not in ('identity','generic','clothing','background','style'):raise ValueError('Choose a supported reference category.')
        return self._write({**prior,'name':name,'references':cards,'category':category,
            'notes':str(data.get('notes',prior.get('notes','')))[:3000],'tags':str(data.get('tags',prior.get('tags','')))[:500]})

    def trash(self,ident,value):
        if type(value) is not bool:raise ValueError('Choose Trash or Restore.')
        return self._write({**self.get(ident),'trashed':value})

    def select(self,ident,indices):
        item=self.get(ident)
        if not item['references']:raise ValueError('Decode this latent-only RefMod into reference pictures first.')
        if not isinstance(indices,list) or not 1<=len(indices)<=8 or len(set(indices))!=len(indices) or any(type(i) is not int or not 0<=i<len(item['references']) for i in indices):
            raise ValueError('Choose one to eight unique pictures.')
        cards=[{**item['references'][i],'enabled':True} for i in indices]
        if item['notes'] and item['notes'] not in cards[0]['note']:
            cards[0]['note']=(cards[0]['note']+' '+item['notes']).strip()[:2000]
        return cards

    def _import_tensor(self,data,name):
        info=inspect_bytes(data);ident=uuid.uuid4().hex
        path=safe_path(self.mod_root,f'sprite_studio/import_{ident}.safetensors');path.parent.mkdir(parents=True,exist_ok=True)
        partial=path.with_suffix('.part');partial.write_bytes(data);partial.replace(path)
        title=str(info['metadata'].get('name') or name)
        if re.fullmatch('[0-9a-f]{32}',title):title=str(info['members'][0].get('name') or Path(name).stem)
        if re.fullmatch('[0-9a-f]{32}(_[0-9]+)?',title):title=Path(name).stem
        return self._write({'id':ident,'name':title[:160],'kind':'refmod','references':[],
            'member_count':info['member_count'],'mod_name':f'sprite_studio/import_{ident}',
            'category':'identity','notes':str(info['members'][0].get('description',''))[:3000],
            'tags':'','trashed':False,'encoding':'Original MiniMax H3 video VAE; imported provenance is supplied by the file.'})

    def import_file(self,data,name):
        if not data or len(data)>MAX_FILE:raise ValueError('Choose a reference package up to 256 MB.')
        if name.lower().endswith('.safetensors'):return self._import_tensor(data,name)
        if not name.lower().endswith('.zip'):raise ValueError('Choose a .safetensors RefMod or Sprite Studio .zip package.')
        try:
            with zipfile.ZipFile(BytesIO(data)) as bundle:
                files=bundle.infolist()
                if len(files)>12 or len({f.filename for f in files})!=len(files) or sum(f.file_size for f in files)>MAX_FILE:
                    raise ValueError('Reference package is too large or contains duplicate files.')
                manifest_info=bundle.getinfo('manifest.json')
                if manifest_info.file_size>100000:raise ValueError('Reference package metadata is too large.')
                package=json.loads(bundle.read('manifest.json'))
                if package.get('schema')!=1:raise ValueError('Unsupported reference package version.')
                item=package['entry'];cards=item.get('references',[])
                if not isinstance(cards,list) or len(cards)>8:raise ValueError('A package supports up to eight pictures.')
                allowed={'manifest.json','refmod.safetensors'}|{f'references/{i}.source' for i in range(len(cards))}
                if any(f.filename not in allowed for f in files):raise ValueError('Unexpected files in reference package.')
                imported=None
                if 'refmod.safetensors' in bundle.namelist():imported=self._import_tensor(bundle.read('refmod.safetensors'),item.get('name','RefMod'))
                references=[]
                for i,card in enumerate(cards):
                    info=bundle.getinfo(f'references/{i}.source')
                    if info.file_size>32*1024*1024:raise ValueError('A reference image exceeds 32 MB.')
                    asset=self.references.import_image(bundle.read(info),f'{item.get("name","Reference")} {i+1}')
                    references.append({**card,'asset_id':asset['id']})
                if imported:imported=self._write({**imported,'references':references})
                return self.save({**item,'id':imported['id'] if imported else None,'references':references})
        except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,json.JSONDecodeError) as error:
            raise ValueError('Invalid Sprite Studio reference package.') from error

    def tensor_file(self,ident):
        item=self.get(ident)
        if item['kind']!='refmod':raise ValueError('This collection has not been encoded into a RefMod yet.')
        path=safe_path(self.mod_root,item['mod_name']+'.safetensors')
        if not path.is_file():raise ValueError('The saved RefMod file is missing.')
        return path

    def export(self,ident):
        item=self.get(ident);path=self.store.path(f'library_exports/{uuid.uuid4().hex}.zip');path.parent.mkdir(parents=True,exist_ok=True)
        partial=path.with_suffix('.part')
        with zipfile.ZipFile(partial,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr('manifest.json',json.dumps({'schema':1,'entry':item},ensure_ascii=False,indent=2))
            if item['kind']=='refmod':bundle.write(self.tensor_file(ident),'refmod.safetensors')
            for i,card in enumerate(item['references']):
                original=self.store.get_document('asset_originals',card['asset_id'])
                source=self.store.path(original['path']) if original else self.references.file(card['asset_id'])
                bundle.write(source,f'references/{i}.source')
        partial.replace(path)
        self.store.put_document('library_exports',path.stem,{'path':f'library_exports/{path.name}'})
        return path

    def export_file(self,ident):
        self.identifier(ident);record=self.store.get_document('library_exports',ident)
        if not record:raise ValueError('Export is unavailable.')
        return self.store.path(record['path'])

    def recipe(self,data):
        recipe=validate(data)
        if recipe['operation']=='decode':
            item=self.get(data.get('library_id'));self.tensor_file(item['id'])
            recipe.update({'library_id':item['id'],'mod_name':item['mod_name'],'member_count':item['member_count']})
        return recipe

    def graph(self,recipe,files,run_id):return build_graph(recipe,files,run_id)

    def complete(self,run,outputs):
        recipe=run['recipe']
        if recipe['operation']=='create':
            path=safe_path(self.mod_root,f'sprite_studio/{run["id"]}.safetensors')
            info=inspect_bytes(path.read_bytes())
            item={'id':run['id'],'name':recipe['prompt'],'references':active_cards(recipe),'category':recipe['refmod']['concept_type'],'notes':recipe['notes'],'tags':recipe['tags'],'trashed':False}
            return self._write({**item,'kind':'refmod','member_count':info['member_count'],'mod_name':f'sprite_studio/{run["id"]}',
                'encoding':'Original MiniMax H3 video VAE (INT8); independent still members','settings':recipe['refmod']})
        item=self.get(recipe['library_id']);cards=[]
        if item.get('decoded_from_run')==run['id']:return item
        for i,output in enumerate(sorted(outputs,key=lambda image:image['filename'])):
            folder=str(output.get('subfolder','')).replace('\\','/')
            if folder!=f'sprite_studio/{run["id"]}' or Path(output['filename']).name!=output['filename']:raise ValueError('Decoded picture is outside its Studio job.')
            path=safe_path(self.output_root,folder+'/'+output['filename'])
            asset=self.references.import_image(path.read_bytes(),f'{item["name"]} decoded {i+1}')
            cards.append({'asset_id':asset['id'],'role':'identity','note':item['notes'][:2000],'enabled':True})
        if len(cards)!=item['member_count']:raise ValueError('Decode did not return every still reference.')
        return self._write({**item,'references':cards,'decoded':True,'decoded_from_run':run['id']})
