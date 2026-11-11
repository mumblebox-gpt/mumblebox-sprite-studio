import importlib
from pathlib import Path
import tempfile
import unittest


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        try:
            self.module = importlib.import_module('sprite_studio.storage')
        except ModuleNotFoundError:
            self.fail('Persistent StudioStore is not implemented')
        self.store = self.module.StudioStore(Path(self.temp.name))
        self.addCleanup(self.store.close)

    def test_drafts_survive_reopen_and_tabs_do_not_share_state(self):
        self.store.put_document('drafts', 'create_image', {'prompt': 'first'})
        self.store.put_document('drafts', 'turnaround', {'prompt': 'second'})
        other = self.module.StudioStore(Path(self.temp.name))
        self.addCleanup(other.close)
        self.assertEqual(other.get_document('drafts', 'create_image')['prompt'], 'first')
        self.assertEqual(other.get_document('drafts', 'turnaround')['prompt'], 'second')

    def test_paths_cannot_escape_owned_root(self):
        for path in ('../private.txt', '/outside', 'C:/outside', 'safe/../../private.txt'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.store.path(path)

    def test_saved_run_is_snapshot_and_list_is_bounded(self):
        recipe = {'prompt': 'Original', 'seed': '42'}
        self.store.create_run('a'*32, recipe, 'request-one')
        recipe['prompt'] = 'Changed'
        self.assertEqual(self.store.get_run('a'*32)['recipe']['prompt'], 'Original')
        self.assertEqual(self.store.by_request('request-one')['id'], 'a'*32)
        with self.assertRaises(ValueError):
            self.store.list_runs(limit=1000)


if __name__ == '__main__':
    unittest.main()
