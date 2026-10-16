"""Single-pass literal embedding keeps payloads and overlapping links intact."""
import unittest

from build_site import replace_literals_once


class StandaloneEmbeddingTests(unittest.TestCase):
    def test_exact_literals_preserve_payload_bytes_and_unrelated_text(self):
        page = '<p>Open &amp; café 🌱</p><img src="art[1].webp"><img src="artX1Ywebp">'
        payload = r'src="data:image/webp;base64,A+/=\1\g<name>"'
        self.assertEqual(
            replace_literals_once(page, {'src="art[1].webp"': payload}),
            '<p>Open &amp; café 🌱</p><img ' + payload + '><img src="artX1Ywebp">',
        )

    def test_specific_evidence_link_precedes_generic_download(self):
        page = ('<a href="data/hn_evidence.json">View evidence</a>'
                '<a href="data/hn_evidence.json">HN evidence</a>')
        replacements = {
            'href="data/hn_evidence.json">View evidence': 'href="#hn-evidence">View evidence',
            'href="data/hn_evidence.json"': 'download="hn_evidence.json" href="data:application/json;base64,e30="',
        }
        self.assertEqual(
            replace_literals_once(page, replacements),
            '<a href="#hn-evidence">View evidence</a>'
            '<a download="hn_evidence.json" href="data:application/json;base64,e30=">HN evidence</a>',
        )

    def test_whole_tag_match_wins_and_embedded_content_is_not_rescanned(self):
        tag = '<img class="category-art" src="domains/test-s.webp">'
        embedded = '<img class="category-art" src="data:image/webp;base64,AA==">'
        css = '<style>/* href="./" src="domains/test-s.webp" */</style>'
        replacements = {
            tag: embedded,
            '<link rel="stylesheet" href="styles.css?v=preview">': css,
            'src="domains/test-s.webp"': 'src="other.webp"',
            'href="./"': 'href="#page-title"',
            '<a href="standalone.html" download>Download</a>': '',
        }
        page = (tag + tag + '<link rel="stylesheet" href="styles.css?v=preview">'
                '<a href="./">Home</a><a href="standalone.html" download>Download</a>')
        self.assertEqual(
            replace_literals_once(page, replacements),
            embedded + embedded + css + '<a href="#page-title">Home</a>',
        )

    def test_no_replacements_or_matches_leave_input_unchanged(self):
        page = '<p>Unchanged</p>'
        self.assertEqual(replace_literals_once(page, {}), page)
        self.assertEqual(replace_literals_once(page, {'absent': 'replacement'}), page)


if __name__ == '__main__':
    unittest.main()
