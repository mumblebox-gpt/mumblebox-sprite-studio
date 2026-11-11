import importlib
import json
from io import BytesIO
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image
from sprite_studio.storage import StudioStore
from sprite_studio.features.references.service import ReferenceAssets


def visual_file(kind='image',version=4):
    shape=[1,24,1,4,4]
    meta={'_format_version':version,'kind':kind,'name':'robot','latent_h':4,'latent_w':4,'latent_t':1,'mode':'encode'}
    header=json.dumps({'__metadata__':{'refmod_meta':json.dumps(meta)},'latent':{'dtype':'F16','shape':shape,'data_offsets':[0,768]}}).encode()
    header+=b' '*(-len(header)%8)
    return struct.pack('<Q',len(header))+header+b'\0'*768


class RefmodTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('sprite_studio.features.refmods.service')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.store=StudioStore(root/'data');self.addCleanup(self.store.close)
        self.assets=ReferenceAssets(self.store,root/'input')
        self.library=self.module.RefModLibrary(self.store,self.assets,root/'mods',root/'output')

    def picture(self):
        image=BytesIO();Image.new('RGB',(64,64),'orange').save(image,format='PNG')
        return self.assets.import_image(image.getvalue(),'robot.png')

    def test_collection_reuse_is_copy_on_use_and_package_keeps_originals(self):
        asset=self.picture()
        saved=self.library.save({'name':'Copper robot','references':[{'asset_id':asset['id'],'role':'identity','note':'red LEFT arm'}]})
        cards=self.library.select(saved['id'],[0]);cards[0]['note']='changed'
        self.assertEqual(self.library.get(saved['id'])['references'][0]['note'],'red LEFT arm')
        package=self.library.export(saved['id'])
        imported=self.library.import_file(package.read_bytes(),'robot.sprite-refmod.zip')
        copied=imported['references'][0]['asset_id']
        original=self.store.get_document('asset_originals',copied)
        self.assertEqual(self.store.path(original['path']).read_bytes(),self.store.path(self.store.get_document('asset_originals',asset['id'])['path']).read_bytes())

    def test_latent_import_validates_header_modality_and_shape_without_decode(self):
        saved=self.library.import_file(visual_file(),'robot.safetensors')
        self.assertEqual(saved['kind'],'refmod');self.assertEqual(saved['member_count'],1)
        self.assertEqual(saved['references'],[])
        for bad in (visual_file('audio'),visual_file(version=99),b'not a tensor',struct.pack('<Q',100000000)):
            with self.subTest(bad=bad[:12]),self.assertRaises(ValueError):self.library.import_file(bad,'invalid.safetensors')
        with self.assertRaises(ValueError):self.library.select(saved['id'],[0])

    def test_graph_uses_original_video_vae_and_separate_owned_branch(self):
        workflow=importlib.import_module('sprite_studio.features.refmods.workflow')
        asset=self.picture();recipe=self.library.recipe({'prompt':'Copper robot','references':[{'asset_id':asset['id']}],'refmod':{}})
        graph=workflow.build_graph(recipe,[asset['filename']],'a'*32)
        self.assertTrue(all(500<=int(key)<700 for key in graph))
        self.assertEqual(graph['501']['inputs']['vae_name'],'minimax_h3_video_vae_int8_convrot.safetensors')
        self.assertEqual(graph['502']['inputs']['mode'],'Full Reference')
        self.assertFalse(graph['502']['inputs']['save'])
        self.assertEqual(graph['503']['class_type'],'MiniMaxH3RefModBundleSave')
        self.assertEqual(graph['503']['inputs']['name'],'a'*32)
