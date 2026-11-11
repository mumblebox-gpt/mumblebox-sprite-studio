from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from sprite_studio.storage import StudioStore
from sprite_studio.features.references.service import ReferenceAssets
from sprite_studio.features.create_image.schema import validate_recipe
from sprite_studio.features.turnaround.service import TurnaroundExports


class AssetTests(unittest.TestCase):
    def test_uploaded_original_bytes_are_preserved_separately(self):
        with tempfile.TemporaryDirectory() as temp:
            store=StudioStore(Path(temp)/'data')
            try:
                service=ReferenceAssets(store,Path(temp)/'input')
                buffer=BytesIO();Image.new('RGBA',(64,64),(1,2,3,80)).save(buffer,format='PNG')
                asset=service.import_image(buffer.getvalue(),'Reference.png')
                original=store.get_document('asset_originals',asset['id'])
                self.assertEqual(store.path(original['path']).read_bytes(),buffer.getvalue())
                self.assertTrue(service.file(asset['id']).is_file())
                with Image.open(service.file(asset['id'])) as normalized:
                    # Transparent references use the same neutral canvas as sheets.
                    self.assertEqual(normalized.getpixel((0,0)),(138,138,138))
            finally: store.close()

    def test_windows_native_output_can_be_reviewed_without_path_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=StudioStore(root/'data');run_id='a'*32
            try:
                path=root/f'output/sprite_studio/{run_id}/master.png';path.parent.mkdir(parents=True);Image.new('RGB',(4096,1024)).save(path)
                recipe=validate_recipe({'kind':'turnaround','prompt':'robot','width':4096,'height':1024})
                store.create_run(run_id,recipe,'one');store.update_run(run_id,'completed',{'outputs':[{'filename':'master.png','subfolder':f'sprite_studio\\{run_id}','type':'output'}]})
                service=TurnaroundExports(store,root/'output')
                self.assertEqual(service.review(run_id)['size'],[4096,1024])
                result=service.export(run_id,service.review(run_id)['rectangles'],True)
                self.assertEqual(result['manifest']['recipe'],recipe)
                self.assertEqual(result['manifest']['reference_mapping'],[])
                self.assertEqual(result['manifest']['master_file'],'master.png')
                import zipfile
                with zipfile.ZipFile(service.file(result['id'])) as bundle:
                    self.assertIn('master.png',bundle.namelist())
                from sprite_studio.features.refmods.service import RefModLibrary
                references=ReferenceAssets(store,root/'input')
                library=RefModLibrary(store,references,root/'mods',root/'output')
                collection=service.to_library(run_id,service.review(run_id)['rectangles'],True,'Robot views',references,library)
                self.assertEqual(len(collection['references']),4)
                self.assertEqual(collection['references'][0]['role'],'identity')
                self.assertEqual(collection['references'][1]['role'],'construction')
                store.update_run(run_id,'completed',{'outputs':[{'filename':'master.png','subfolder':'../private','type':'output'}]})
                with self.assertRaises(ValueError): service.review(run_id)
            finally: store.close()
