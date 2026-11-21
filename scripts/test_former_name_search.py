import unittest
import build_site


class FormerNameSearchTests(unittest.TestCase):
    def test_index_keeps_only_software_names_and_deduplicates(self):
        project = {'id': 'a' * 64, 'name': 'OpenQuill', 'description': 'Dictation',
                   'categories': [], 'history': [
                       {'kind': 'software_rename', 'old_name': 'Open Whisper'},
                       {'kind': 'software_rename', 'old_name': 'Open Whisper'},
                       {'kind': 'repository_rename', 'old_name': 'owner/path'},
                       {'kind': 'owner_transfer', 'old_name': 'old-owner'}]}
        catalog = {'projects': [project], 'metrics_as_of': None, 'categories': []}
        item = build_site.search_index(catalog)['projects'][0]
        self.assertEqual(item['former_names'], ['Open Whisper'])
        self.assertNotIn('history', item)
        self.assertEqual(project['name'], 'OpenQuill')
        project['history'] = []
        self.assertNotIn('former_names', build_site.search_index(catalog)['projects'][0])
