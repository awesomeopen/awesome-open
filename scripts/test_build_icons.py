"""Icon SVGs: manifest coverage, colour-free markup, grid sizes, committed files current."""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from build_icons import DRAW, MANIFEST, OUTPUT, SIZES, build

PX = {key: value[0] for key, value in SIZES.items()}


class BuildIconsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.icons = json.loads(MANIFEST.read_text(encoding="utf-8"))["icons"]
        cls.temp = tempfile.TemporaryDirectory()
        cls.written = build(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_today_icon_has_a_drawing(self):
        today = {i["id"] for i in self.icons if i["status"] == "today"}
        self.assertEqual(today, set(DRAW))

    def test_one_file_per_listed_size(self):
        expected = {f"{i['id']}-{s}.svg" for i in self.icons if i["id"] in DRAW for s in i["sizes"]}
        self.assertEqual(expected, {p.name for p in self.written})

    def test_markup_is_sized_and_colour_free(self):
        for path in self.written:
            text = path.read_text(encoding="utf-8")
            root = ET.fromstring(text)
            px = PX[path.stem.rsplit("-", 1)[1]]
            self.assertEqual(root.get("viewBox"), f"0 0 {px} {px}", path.name)
            self.assertEqual(root.get("aria-hidden"), "true", path.name)
            stripped = text.replace('fill="#fff"', "").replace('fill="#000"', "")  # mask channels only
            self.assertNotRegex(stripped, r"#[0-9A-Fa-f]{3,6}\b", path.name)
            self.assertNotIn("<image", text, path.name)

    def test_committed_files_match_the_generator(self):
        for path in self.written:
            committed = OUTPUT / path.name
            self.assertTrue(committed.is_file(), f"missing {committed}; run scripts/build_icons.py")
            self.assertEqual(committed.read_text(encoding="utf-8"), path.read_text(encoding="utf-8"), path.name)
        stray = {p.name for p in OUTPUT.glob("*.svg")} - {p.name for p in self.written}
        self.assertFalse(stray, f"unlisted icon files: {sorted(stray)}")


if __name__ == "__main__":
    unittest.main()
