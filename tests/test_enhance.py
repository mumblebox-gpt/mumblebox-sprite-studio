import importlib
import unittest


class EnhanceTests(unittest.TestCase):
    def test_enhancement_preserves_draft_and_passes_constraints_separately(self):
        service=importlib.import_module('sprite_studio.features.enhance.service')
        draft={'kind':'turnaround','prompt':'A copper robot','references':[{'note':'red band on LEFT arm'}],
               'turnaround':{'locks':'two antennas','preset':'cardinal'}}
        messages=service.messages_for(draft)
        self.assertIn('120',messages[0]['content'])
        self.assertIn('red band on LEFT arm',messages[1]['content'])
        self.assertIn('two antennas',messages[1]['content'])
        self.assertEqual(draft['prompt'],'A copper robot')
        self.assertIn('Do not add scenery',messages[0]['content'])

    def test_candidate_schema_is_bounded_and_rejects_truncated_output(self):
        service=importlib.import_module('sprite_studio.features.enhance.service')
        self.assertEqual(service.read_candidate({'content':'{"prompt":"A copper robot with crisp enamel."}','stop_type':'eos'}),'A copper robot with crisp enamel.')
        with self.assertRaises(ValueError):service.read_candidate({'content':'{"prompt":"unfinished"}','stop_type':'limit'})
        with self.assertRaises(ValueError):service.read_candidate({'content':'{"prompt":""}'})
