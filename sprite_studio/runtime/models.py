"""Select only the components used by a recipe; reuse qualified installed files."""
import json
from pathlib import Path
from .downloads import download_file, sha256
from ..features.create_image.workflow import model_names
from ..features.enhance.service import MODEL_NAME

CATALOG = json.loads((Path(__file__).parent/'model_catalog.json').read_text(encoding='utf-8-sig'))


def required_files(recipe):
    if recipe.get('kind')=='enhance':
        return [spec for spec in CATALOG['files'] if spec['path']=='text_encoders/'+MODEL_NAME]
    if recipe.get('kind')=='refmod':
        return [spec for spec in CATALOG['files'] if spec['path']=='vae/minimax_h3_video_vae_int8_convrot.safetensors']
    names = model_names(recipe['profile'])
    paths = {f'{folder}/{name}' for folder,name in names.items()}
    if recipe['upsample']:
        suffix = 'w4a8' if recipe['upsampler_precision']=='w4a8' else 'int8_convrot'
        paths.add(f'text_encoders/p-h3-image_prompt_upsampler_{suffix}.safetensors')
    return [spec for spec in CATALOG['files'] if spec['path'] in paths]


class ModelDownloads:
    def __init__(self, store, model_root, resolve):
        self.store = store
        self.model_root = Path(model_root)
        self.resolve = resolve

    def ensure(self, recipe, progress, cancel):
        for spec in required_files(recipe):
            folder,name = spec['path'].split('/',1)
            existing = self.resolve(folder,name)
            existing = Path(existing) if existing else None
            if existing and existing.is_file():
                stat = existing.stat()
                key = str(existing.resolve())
                receipt = self.store.get_document('verified_models',key,{})
                fingerprint = {'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':spec['sha256']}
                if receipt == fingerprint:
                    progress({'stage':'ready','file':name,'bytes':stat.st_size,'total':spec['size']})
                    continue
                if stat.st_size != spec['size'] or sha256(existing,cancel,progress) != spec['sha256']:
                    raise ValueError(f'{name} differs from the selected publisher file. Existing model was preserved.')
                self.store.put_document('verified_models',key,fingerprint)
                continue
            path = download_file(spec,self.model_root,progress,cancel)
            stat = path.stat()
            self.store.put_document('verified_models',str(path.resolve()),{'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':spec['sha256']})

    def inventory(self):
        return [{'path':spec['path'],'size':spec['size'],'installed':bool(self.resolve(*spec['path'].split('/',1))),
                 'sources':[url.split('/')[2] for url in spec['urls']]} for spec in CATALOG['files']]
