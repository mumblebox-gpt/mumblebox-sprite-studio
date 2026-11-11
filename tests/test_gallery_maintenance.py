from pathlib import Path
import importlib
import tempfile
import unittest
from sprite_studio.storage import StudioStore


class GalleryTests(unittest.TestCase):
    def test_bulk_trash_restore_does_not_change_recipe_or_assets(self):
        module=importlib.import_module('sprite_studio.features.gallery.service')
        with tempfile.TemporaryDirectory() as temp:
            store=StudioStore(temp)
            try:
                run=store.create_run('a'*32,{'kind':'create_image','prompt':'Robot'},'first')
                store.update_run(run['id'],'completed',{'outputs':[]})
                gallery=module.Gallery(store)
                gallery.update(run['id'],{'name':'Copper Robot','favorite':True})
                gallery.trash([run['id']],True)
                self.assertEqual(gallery.list()['runs'],[])
                self.assertEqual(gallery.list(trashed=True)['runs'][0]['recipe'],run['recipe'])
                gallery.trash([run['id']],False)
                self.assertEqual(gallery.list(favorite=True)['runs'][0]['name'],'Copper Robot')
                store.create_run('b'*32,{'kind':'create_image','prompt':'Active'},'second')
                with self.assertRaises(ValueError): gallery.trash(['b'*32],True)
            finally:store.close()


class MaintenanceTests(unittest.TestCase):
    def test_purge_only_unleased_scratch_and_protects_saved_assets(self):
        module=importlib.import_module('sprite_studio.runtime.temporary')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);saved=root/'originals/keep.png';saved.parent.mkdir();saved.write_bytes(b'keep')
            owner=module.TemporaryFiles(root/'temporary')
            abandoned=owner.root/('a'*32);abandoned.mkdir();(abandoned/'partial.tmp').write_bytes(b'old-data')
            with owner.lease() as leased:
                (leased/'active.tmp').write_bytes(b'active')
                result=owner.purge()
                self.assertEqual(result['bytes'],8)
                self.assertTrue((leased/'active.tmp').is_file())
                self.assertEqual(saved.read_bytes(),b'keep')
            self.assertEqual(owner.purge()['bytes'],6)
