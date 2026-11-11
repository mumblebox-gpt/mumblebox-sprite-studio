"""Import immutable local picture copies for native LoadImage and library reuse."""
import hashlib
from io import BytesIO
from pathlib import Path
import uuid
from PIL import Image, ImageOps
from ...storage import safe_path


class ReferenceAssets:
    def __init__(self, store, input_root):
        self.store = store
        self.input_root = Path(input_root)
        (self.input_root/'sprite_studio').mkdir(parents=True,exist_ok=True)

    def import_image(self, data, name):
        if not data or len(data)>32*1024*1024:
            raise ValueError('Choose an image up to 32 MB.')
        with Image.open(BytesIO(data)) as source:
            if source.width*source.height>32_000_000 or source.format not in ('PNG','JPEG','WEBP','BMP','TIFF'):
                raise ValueError('Choose a PNG, JPEG, WebP, BMP or TIFF up to 32 megapixels.')
            oriented = ImageOps.exif_transpose(source).convert('RGBA')
            background = Image.new('RGBA',oriented.size,(200,200,200,255))
            picture = Image.alpha_composite(background,oriented).convert('RGB')
            asset_id = uuid.uuid4().hex
            original = self.store.path(f'originals/{asset_id}.source')
            original.parent.mkdir(parents=True,exist_ok=True)
            original.write_bytes(data)
            filename = f'sprite_studio/{asset_id}.png'
            target = safe_path(self.input_root,filename)
            partial = target.with_suffix('.tmp')
            picture.save(partial,format='PNG')
            partial.replace(target)
            asset = {'id':asset_id,'filename':filename,'name':str(name)[:240],
                     'digest':hashlib.sha256(data).hexdigest(),'width':picture.width,'height':picture.height}
        self.store.add_asset(asset)
        self.store.put_document('asset_originals',asset_id,{'path':f'originals/{asset_id}.source','name':asset['name'],'format':source.format,'digest':asset['digest']})
        return asset

    def file(self, asset_id):
        return safe_path(self.input_root,self.store.get_asset(asset_id)['filename'])
