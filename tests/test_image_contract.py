import importlib
import unittest


def owner(test, name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        test.fail(f"Required behavior owner is not implemented: {error.name}")


class ImageContractTests(unittest.TestCase):
    def setUp(self):
        self.schema = owner(self, 'sprite_studio.features.create_image.schema')
        self.prompt = owner(self, 'sprite_studio.features.create_image.prompt')
        self.workflow = owner(self, 'sprite_studio.features.create_image.workflow')

    def test_fixed_seed_survives_javascript_integer_limit(self):
        result = self.schema.validate_recipe({'prompt': 'A red shuttle', 'seed': '18446744073709551615', 'seed_mode': 'fixed'})
        self.assertEqual(result['seed'], '18446744073709551615')
        self.assertEqual(result['profile'], 'w4a8')
        with self.assertRaises(ValueError):
            self.schema.validate_recipe({'prompt': 'ship', 'seed': '18446744073709551616', 'seed_mode': 'fixed'})

    def test_dimensions_and_distilled_schedule_are_validated(self):
        for data in ({'width': 1000}, {'height': 0}, {'sigmas': '1,0.5,0.7,0'}, {'sigmas': '1,nan,0'}, {'profile': 'bf16'}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.schema.validate_recipe({'prompt': 'ship', **data})

    def test_disabled_references_do_not_shift_instruction_identity(self):
        recipe = self.schema.validate_recipe({'prompt': 'Make a neutral full-body character', 'references': [
            {'asset_id': 'a'*32, 'role': 'identity', 'note': 'Preserve the blue eyes', 'enabled': True},
            {'asset_id': 'b'*32, 'role': 'style', 'note': 'UNUSED', 'enabled': False},
            {'asset_id': 'c'*32, 'role': 'clothing', 'note': 'Use this orange jacket', 'enabled': True}]})
        prompt = self.prompt.build_prompt(recipe)
        self.assertIn('<Picture 1>', prompt)
        self.assertIn('<Picture 2>', prompt)
        self.assertNotIn('<Picture 3>', prompt)
        self.assertNotIn('UNUSED', prompt)
        self.assertLess(prompt.index('blue eyes'), prompt.index('orange jacket'))

    def test_reference_limit_counts_enabled_cards(self):
        cards = [{'asset_id': f'{n:032x}', 'enabled': True} for n in range(9)]
        with self.assertRaises(ValueError):
            self.schema.validate_recipe({'prompt': 'ship', 'references': cards})
        cards[-1]['enabled'] = False
        self.assertEqual(len(self.schema.validate_recipe({'prompt': 'ship', 'references': cards})['references']), 9)

    def test_native_branch_uses_vae_reference_and_matching_precision(self):
        recipe = self.schema.validate_recipe({'prompt': 'A shuttle', 'profile': 'int8', 'seed_mode': 'fixed', 'seed': '42', 'references': [{'asset_id': 'a'*32}]})
        graph = self.workflow.build_prompt_graph(recipe, ['sprite_studio/a.png'], 'r'*32)
        kinds = {node['class_type'] for node in graph.values()}
        self.assertTrue({'PH3ImageConditioning', 'MiniMaxH3SigmaShift', 'SamplerCustomAdvanced', 'VAEDecode', 'SaveImage'} <= kinds)
        condition = next(n['inputs'] for n in graph.values() if n['class_type'] == 'PH3ImageConditioning')
        self.assertIn('vae', condition)
        self.assertIn('images.image_1', condition)
        model = next(n['inputs'] for n in graph.values() if n['class_type'] == 'UNETLoader')
        self.assertEqual(model['unet_name'], 'p-h3-image_int8_convrot.safetensors')
        self.assertNotIn('KSampler', kinds)
        for node in graph.values():
            for value in node['inputs'].values():
                if isinstance(value, list):
                    self.assertIn(str(value[0]), graph)

    def test_decode_and_sampled_upsampler_controls_reach_native_nodes(self):
        recipe=self.schema.validate_recipe({'prompt':'A shuttle','upsample':True,'upsampler_sampling':True,
            'upsampler_seed':'18446744073709551615','upsampler_temperature':0.4,'decode_mode':'tiled','tile_size':768,'tile_overlap':64})
        graph=self.workflow.build_prompt_graph(recipe,[],'a'*32)
        helper=graph['141']['inputs']
        self.assertEqual(helper['sampling_mode'],'on')
        self.assertEqual(helper['sampling_mode.seed'],2**64-1)
        self.assertEqual(helper['sampling_mode.temperature'],0.4)
        self.assertEqual(graph['111']['class_type'],'VAEDecodeTiled')
        self.assertEqual(graph['111']['inputs']['tile_size'],768)
        with self.assertRaises(ValueError):self.schema.validate_recipe({'prompt':'ship','decode_mode':'tiled','tile_overlap':768,'tile_size':512})


if __name__ == '__main__':
    unittest.main()
