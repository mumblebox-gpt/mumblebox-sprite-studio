import importlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from sprite_studio.features.create_image.schema import validate_recipe
from sprite_studio.features.create_image.prompt import build_prompt
from sprite_studio.features.create_image.workflow import build_prompt_graph


class TurnaroundTests(unittest.TestCase):
    def test_cardinal_prompt_locks_identity_handedness_and_camera(self):
        recipe=validate_recipe({'kind':'turnaround','prompt':'Copper robot with a red LEFT forearm',
            'width':4096,'height':1024,'turnaround':{'preset':'cardinal','subject':'character'}})
        prompt=build_prompt(recipe)
        for fragment in ('0°','90°','180°','270°','red LEFT forearm','same subject','Do not mirror','four equal'):
            self.assertIn(fragment,prompt)
        self.assertEqual(recipe['turnaround']['views'][1]['label'],'left')
        graph=build_prompt_graph(recipe,[],'a'*32)
        self.assertTrue(all(300<=int(key)<500 for key in graph))

    def test_custom_angles_and_layout_reject_invalid_values(self):
        for config in ({'views':[{'label':'front','azimuth':float('nan')}]}, {'columns':0}, {'elevation':100}):
            with self.subTest(config=config),self.assertRaises(ValueError):
                validate_recipe({'kind':'turnaround','prompt':'Robot','turnaround':{'preset':'custom',**config}})

    def test_sheet_crops_cover_exact_cells_without_overlap(self):
        crops=importlib.import_module('sprite_studio.features.turnaround.crops')
        result=crops.default_crops(4096,1024,4,4)
        self.assertEqual(result,[[0,0,1024,1024],[1024,0,2048,1024],[2048,0,3072,1024],[3072,0,4096,1024]])
        with self.assertRaises(ValueError): crops.validate_crops([[0,0,4097,1024]],4096,1024,1)

    def test_export_preserves_pixel_scale_and_records_requested_angles(self):
        crops=importlib.import_module('sprite_studio.features.turnaround.crops')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'master.png';Image.new('RGB',(200,100),'red').save(source)
            views=[{'label':'front','azimuth':0},{'label':'left','azimuth':90}]
            manifest=crops.export_images(source,root/'export',[[0,0,80,100],[100,0,200,100]],views,{'projection':'orthographic'})
            with Image.open(root/'export/front.png') as result: self.assertEqual(result.size,(100,100))
            self.assertEqual(manifest['camera_provenance'],'requested, not measured')
            self.assertFalse(manifest['independently_rescaled'])
            self.assertEqual(json.loads((root/'export/manifest.json').read_text())['views'][1]['azimuth'],90)


class UpsamplerTests(unittest.TestCase):
    def test_helper_off_needs_no_helper_branch(self):
        graph=build_prompt_graph(validate_recipe({'prompt':'A robot'}),[],'a'*32)
        self.assertNotIn('TextGenerateV2',[n['class_type'] for n in graph.values()])

    def test_helper_uses_all_active_images_and_records_actual_prompt(self):
        recipe=validate_recipe({'prompt':'A robot','upsample':True,'references':[{'asset_id':'a'*32},{'asset_id':'b'*32}]})
        graph=build_prompt_graph(recipe,['a.png','b.png'],'a'*32)
        helpers=[(key,n) for key,n in graph.items() if n['class_type']=='TextGenerateV2']
        self.assertEqual(len(helpers),1)
        key,helper=helpers[0]
        self.assertIn('images.image2',helper['inputs'])
        conditioning=next(n for n in graph.values() if n['class_type']=='PH3ImageConditioning')
        self.assertEqual(conditioning['inputs']['prompt'],[key,0])
        self.assertTrue(any(n['class_type']=='PreviewAny' and n['inputs']['source']==[key,0] for n in graph.values()))
