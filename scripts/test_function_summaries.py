"""Reviewed prose must preserve identity, provenance, fallback and safe rendering."""
from copy import deepcopy
import hashlib
import unittest
from unittest.mock import patch

import build_catalog as catalog
import build_site

class FunctionSummaryTests(unittest.TestCase):
    def setUp(self):
        self.url = 'https://github.com/example/open'
        self.pid = hashlib.sha256(self.url.encode()).hexdigest()
        self.source = '## Tools\n\n| Project | Description |\n| --- | --- |\n| [Open](https://github.com/example/open) | Short description. |\n'
        self.snapshot = {'schema_version': 1, 'as_of': '2026-10-13', 'repositories': {}}
        self.empty = {'schema_version': 1, 'projects': []}
        self.entry = {'project_url': self.url, 'text': ' '.join(['capability']*40),
                      'sources': [{'url': 'https://example.org/docs', 'title': 'Official docs'}],
                      'checked_at': '2026-10-13', 'review_status': 'approved', 'reviewed_by': 'Test'}
        self.document = {'schema_version': 1, 'summaries': {self.pid: self.entry}}

    def build(self, document=None):
        return catalog.build_catalog(self.source, self.snapshot, self.empty, self.empty,
                                     function_summaries=document)

    def plate(self, result):
        """The project's card as its static record writes it, plate included."""
        categories = {c['id']: c['name'] for c in result['categories']}
        return build_site.project_html(result['projects'][0], categories, result)

    def test_approved_is_additive_immutable_and_offline(self):
        before = deepcopy(self.document)
        with patch('urllib.request.urlopen', side_effect=AssertionError('No fetch')):
            result = self.build(self.document)
        p = result['projects'][0]
        self.assertEqual(p['description'], 'Short description.')
        self.assertEqual(p['id'], self.pid)
        self.assertEqual(p['function_summary']['text'], self.entry['text'])
        self.assertEqual(self.document, before)
        self.assertEqual(result, self.build(self.document))
        rendered = self.plate(result)
        self.assertIn('class="function-detail"', rendered)
        self.assertIn('href="https://example.org/docs"', rendered)
        self.assertIn('Reviewed <span class="metric-value">2026-10-13', rendered)

    def test_missing_pending_rejected_fall_back(self):
        for state in (None, 'pending', 'rejected'):
            doc = deepcopy(self.document) if state else None
            if doc:
                doc['summaries'][self.pid]['review_status'] = state
            result = self.build(doc)
            self.assertNotIn('function_summary', result['projects'][0])
            self.assertNotIn('class="function-detail"', self.plate(result))
            self.assertIn('Short description.', build_site.render_html(result))

    def test_invalid_approved_evidence_fails(self):
        mutations = [
            lambda e: e.update(project_url='https://github.com/other/open'),
            lambda e: e.update(text='Too short.'),
            lambda e: e.update(checked_at='2026-02-31'),
            lambda e: e.update(reviewed_by=''),
            lambda e: e.update(sources=[]),
            lambda e: e['sources'][0].update(url='javascript:alert(1)'),
            lambda e: e['sources'][0].update(url='https://user:secret@example.org'),
            lambda e: e['sources'][0].update(revision='main'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                doc = deepcopy(self.document)
                mutate(doc['summaries'][self.pid])
                with self.assertRaises(ValueError):
                    self.build(doc)
        doc = deepcopy(self.document)
        doc['summaries']['0'*64] = doc['summaries'].pop(self.pid)
        with self.assertRaises(ValueError):
            self.build(doc)

    def test_plain_text_is_escaped(self):
        self.entry['text'] += ' <script>alert(1)</script>'
        rendered = self.plate(self.build(self.document))
        self.assertNotIn('<script>alert(1)</script>', rendered)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', rendered)

    def test_feature_requires_reviewed_source_and_safe_plain_text(self):
        self.entry['features'] = [{'title': 'A capability', 'text': '<detail>',
                                  'source_url': self.entry['sources'][0]['url']}]
        result = self.build(self.document)
        self.assertEqual(result['projects'][0]['function_summary']['features'], self.entry['features'])
        self.entry['features'][0]['source_url'] = 'https://unreviewed.example'
        with self.assertRaises(ValueError): self.build(self.document)

    def test_first_complete_name_highlight_preserves_escaping(self):
        rendered = build_site.highlight_name('Opening <text> Open & Open.', 'Open')
        self.assertEqual(rendered, 'Opening &lt;text&gt; <mark class="tool-name">Open</mark> &amp; Open.')

if __name__ == '__main__':
    unittest.main()
