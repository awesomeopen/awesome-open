"""Offline catalog identity, evidence, safety, and reproducibility contracts."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_catalog as catalog
import update_stats as stats


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.row = "| [Open](https://github.com/example/open) | Original description. |\n"
        self.source = "## AI & Language Models\n\n| Project | Description |\n| --- | --- |\n" + self.row
        self.record = {"created_at": "2020-01-01T00:00:00Z", "pushed_at": "2025-10-07T00:00:00Z",
                       "license": {"spdx_id": "MIT"}, "stargazers_count": 1234}
        self.snapshot = {"schema_version": 1, "as_of": "2026-10-07", "repositories": {"example/open": self.record}}
        self.alternatives = {"schema_version": 1, "projects": []}
        self.hn = {"schema_version": 1, "projects": []}

    def build(self, source=None, **kwargs):
        return catalog.build_catalog(self.source if source is None else source, self.snapshot,
                                     self.alternatives, self.hn, **kwargs)

    def add_alternative(self):
        record = {"name": "Other", "source_url": "https://example.com/comparison/",
                  "checked_utc_date": "2026-10-03", "scope": "The exact reviewed use case.",
                  "claimant": "Other", "confidence": "high", "source_quote": "A reviewed comparison.",
                  "target_url": "https://other.example/"}
        self.alternatives["projects"] = [{"readme_url": "https://github.com/example/open", "alternatives": [record]}]
        self.source = self.source.replace("description.", "description.<br>Alternative to: [Other](https://example.com/comparison/)")
        return record

    def add_hn(self, url="https://github.com/example/open", eligible=True):
        record = {"name": "Open", "readme_url": url, "slug": "open", "eligible": eligible,
                  "search_url": "https://hn.algolia.com/?q=Open&type=story", "story_count": 8}
        self.hn["projects"].append(record)
        return record

    def test_schema_metadata_and_counts(self):
        result = self.build()
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["metrics_as_of"], "2026-10-07")
        self.assertIsNone(result["source_sha"])
        self.assertEqual(result["category_memberships"], 1)
        self.assertEqual(result["categories"], [{"id": "ai--language-models", "name": "AI & Language Models", "count": 1}])
        project = result["projects"][0]
        self.assertEqual(project["categories"], ["ai--language-models"])
        self.assertEqual(project["github"], {"repo": "example/open", "stars": 1234, "license": "MIT",
                                          "created_at": self.record["created_at"], "pushed_at": self.record["pushed_at"]})
        self.assertEqual(project["alternatives"], [])
        self.assertIsNone(project["hn"])

    def test_deterministic_offline_without_wall_clock(self):
        inputs = deepcopy((self.source, self.snapshot, self.alternatives, self.hn))
        with patch.object(stats, "utc_today", side_effect=AssertionError("No wall clock")), \
                patch.object(stats.urllib.request, "urlopen", side_effect=AssertionError("No network")):
            first = self.build()
            second = self.build()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(inputs, (self.source, self.snapshot, self.alternatives, self.hn))

    def test_crosslist_canonicalization_preserves_memberships(self):
        variant = self.row.replace("https://github.com/example/open", "https://GitHub.COM/EXAMPLE/Open/")
        result = self.build(self.source + "## Developer Tools\n" + variant)
        self.assertEqual(len(result["projects"]), 1)
        self.assertEqual(result["category_memberships"], 2)
        self.assertEqual(result["projects"][0]["url"], "https://github.com/example/open")
        self.assertEqual(result["projects"][0]["categories"], ["ai--language-models", "developer-tools"])
        self.assertEqual([item["count"] for item in result["categories"]], [1, 1])

    def test_same_category_duplicate_is_one_membership(self):
        result = self.build(self.source + self.row)
        self.assertEqual(result["category_memberships"], 1)
        self.assertEqual(result["categories"][0]["count"], 1)

    def test_same_name_distinct_urls_stay_distinct(self):
        result = self.build(self.source + self.row.replace("example/open", "another/open"))
        self.assertEqual(len(result["projects"]), 2)
        self.assertEqual(len({item["id"] for item in result["projects"]}), 2)

    def test_project_identity_does_not_depend_on_name_or_description(self):
        original = self.build()["projects"][0]["id"]
        changed = self.build(self.source.replace("[Open]", "[Renamed]").replace("Original", "Revised"))
        self.assertEqual(changed["projects"][0]["id"], original)

    def test_non_github_paths_are_case_sensitive(self):
        source = "## Sites\n| [Open](https://EXAMPLE.com/Open/) | Site. |\n| [Open](https://example.com/open) | Site. |\n| [Open](https://example.com/Open) | Site. |\n"
        result = self.build(source)
        self.assertEqual([item["url"] for item in result["projects"]], ["https://example.com/Open", "https://example.com/Open/", "https://example.com/open"])
        self.assertTrue(all(item["github"] is None for item in result["projects"]))

    def test_url_normalization_does_not_lower_query_fragment_or_file_path(self):
        self.assertEqual(catalog.canonical_url("https://GITHUB.com/Org/Repo/tree/Main/File/?q=Name#Section"),
                         "https://github.com/org/repo/tree/Main/File/?q=Name#Section")
        self.assertEqual(catalog.canonical_url("https://Example.com:443/"), "https://example.com")
        self.assertEqual(catalog.canonical_url("http://[::1]:8000/path/"), "http://[::1]:8000/path/")

    def test_trailing_slash_normalization_is_repository_specific(self):
        self.assertEqual(catalog.canonical_url("https://github.com/Org/Repo/"), "https://github.com/org/repo")
        for path in ("/tool", "/tool/", "/tool//"):
            self.assertEqual(catalog.canonical_url("https://example.com" + path), "https://example.com" + path)
        for path in ("/org/repo/issues", "/org/repo/issues/", "/org/repo/tree/Main/"):
            self.assertEqual(catalog.canonical_url("https://github.com" + path), "https://github.com" + path)

    def test_known_github_metadata_uses_normalized_repo_grammar(self):
        source = self.source.replace("https://github.com/example/open", "https://GitHub.COM/EXAMPLE/Open/")
        self.assertEqual(self.build(source)["projects"][0]["github"]["stars"], 1234)

    def test_missing_metrics_and_non_github_are_null(self):
        self.snapshot["repositories"] = {}
        source = self.source + "| [Site](https://example.com) | A hosted site. |\n"
        self.assertTrue(all(item["github"] is None for item in self.build(source)["projects"]))

    def test_unknown_licenses_are_null_not_proprietary(self):
        for value in (None, {"spdx_id": None}, {"spdx_id": ""}, {"spdx_id": "NOASSERTION"}, {"spdx_id": "OTHER"}):
            with self.subTest(value=value):
                self.record["license"] = value
                result = self.build()
                self.assertIsNone(result["projects"][0]["github"]["license"])
                self.assertNotIn("proprietary", json.dumps(result).lower())

    def test_zero_stars_and_missing_push_stay_zero_and_null(self):
        self.record["stargazers_count"] = 0
        self.record["pushed_at"] = None
        github = self.build()["projects"][0]["github"]
        self.assertEqual(github["stars"], 0)
        self.assertIsNone(github["pushed_at"])

    def test_conflicting_duplicate_names_and_descriptions_fail(self):
        for row in (self.row.replace("[Open]", "[Other]"), self.row.replace("Original", "Different")):
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "Conflicting cross-listed"):
                self.build(self.source + "## Two\n" + row)

    def test_reviewed_alternatives_preserve_full_evidence_and_plain_description(self):
        evidence = self.add_alternative()
        result = self.build()["projects"][0]
        self.assertEqual(result["description"], "Original description.")
        self.assertEqual(result["alternatives"], [evidence])
        result["alternatives"][0]["scope"] = "Changed result"
        self.assertEqual(evidence["scope"], "The exact reviewed use case.")

    def test_alternative_evidence_matches_normalized_project_identity(self):
        self.add_alternative()
        self.alternatives["projects"][0]["readme_url"] = "https://GITHUB.com/EXAMPLE/Open/"
        self.assertEqual(len(self.build()["projects"][0]["alternatives"]), 1)

    def test_missing_or_mismatched_alternative_evidence_fails(self):
        self.add_alternative()
        good = deepcopy(self.alternatives)
        mutations = [lambda d: d["projects"].clear(),
                     lambda d: d["projects"][0]["alternatives"][0].update(name="Another"),
                     lambda d: d["projects"][0]["alternatives"][0].update(source_url="https://example.com/other")]
        for mutate in mutations:
            self.alternatives = deepcopy(good)
            mutate(self.alternatives)
            with self.assertRaisesRegex(ValueError, "inconsistent reviewed alternatives"):
                self.build()

    def test_missing_inline_alternative_on_one_crosslist_fails(self):
        self.add_alternative()
        with self.assertRaisesRegex(ValueError, "inconsistent reviewed alternatives"):
            self.build(self.source + "## Two\n" + self.row)

    def test_unused_or_duplicate_evidence_fails(self):
        self.add_alternative()
        with self.assertRaisesRegex(ValueError, "unlisted"):
            self.build("## Empty\n")
        self.alternatives["projects"].append(deepcopy(self.alternatives["projects"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate alternatives"):
            self.build()

    def test_incomplete_alternative_review_fails(self):
        self.add_alternative()
        good = deepcopy(self.alternatives)
        for key, value in (("scope", ""), ("checked_utc_date", "not-a-date"), ("source_url", "http://example.com/"), ("target_url", "javascript:bad")):
            self.alternatives = deepcopy(good)
            self.alternatives["projects"][0]["alternatives"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build()

    def test_hn_matches_exact_canonical_url_and_only_eligible(self):
        self.add_hn("https://GITHUB.com/EXAMPLE/Open/")
        project = self.build()["projects"][0]
        self.assertEqual(project["hn"], {"slug": "open", "chart_url": "assets/hn/open.svg",
                                         "search_url": "https://hn.algolia.com/?q=Open&type=story", "total_stories": 8})
        self.hn["projects"][0]["eligible"] = False
        self.assertIsNone(self.build()["projects"][0]["hn"])

    def test_hn_does_not_attach_by_name_or_lowercase_non_github_path(self):
        self.add_hn("https://example.com/open")
        source = self.source.replace("https://github.com/example/open", "https://example.com/Open")
        self.assertIsNone(self.build(source)["projects"][0]["hn"])

    def test_hn_slug_path_traversal_and_duplicates_fail(self):
        record = self.add_hn()
        for slug in ("../open", "foo/bar", "Open", "open.svg", "", "a\\b"):
            record["slug"] = slug
            with self.subTest(slug=slug), self.assertRaisesRegex(ValueError, "slug"):
                self.build()
        record["slug"] = "open"
        self.hn["projects"].append(deepcopy(record))
        with self.assertRaisesRegex(ValueError, "Duplicate HN"):
            self.build()

    def test_hn_unsafe_search_and_invalid_counts_fail(self):
        record = self.add_hn()
        record["search_url"] = "https://user:secret@example.com/"
        with self.assertRaises(ValueError):
            self.build()
        record["search_url"] = "https://hn.algolia.com/"
        for count in (-1, True, "8"):
            record["story_count"] = count
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.build()

    def test_unsafe_urls_are_rejected(self):
        urls = ["javascript:alert(1)", "//example.com", "https://user:password@example.com/repo",
                "https://user@example.com", "https://example.com/a\tb", "https://example.com/a\nb",
                "https://example.com/%0afoo", "https://example.com/%00foo", "https://exa%0dmple.com",
                "https://example.com/\u0080foo", "https://example.com/%C2%80foo",
                "https://example.com:bad/path", "https:///missing-host", "https://example.com\\@evil.test/"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                catalog.canonical_url(url)
        with self.assertRaises(ValueError):
            self.build(self.source.replace("https://github.com/example/open", "https://user:password@example.com/repo"))

    def test_arbitrary_html_is_text_for_the_html_renderer(self):
        text = '<img src=x onerror="alert(1)"> & </script>'
        source = self.source.replace("[Open]", "[" + text + "]").replace("Original description.", text)
        self.record["license"] = {"spdx_id": text}
        project = self.build(source)["projects"][0]
        self.assertEqual(project["name"], text)
        self.assertEqual(project["description"], text)
        self.assertEqual(project["github"]["license"], text)

    def test_malformed_or_generated_project_rows_fail(self):
        bad_rows = [self.row.replace(" | Original", " | Extra | Original"),
                    self.row.replace("Original description.", "<!-- STATS:START --><!-- STATS:END -->"),
                    self.row.replace("[Open]", "**[Open]").replace(") |", ")** |"),
                    "| Open | Missing project link. |\n", "| [Open](javascript:bad) | Bad URL. |\n",
                    "| [Open](https://example.com) |   |\n", "|[Open](https://example.com) | Bad spacing. |\n"]
        for row in bad_rows:
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.build(self.source.replace(self.row, row))

    def test_entry_before_category_fails(self):
        with self.assertRaisesRegex(ValueError, "heading"):
            self.build(self.row)

    def test_empty_catalog_and_explicit_empty_category_are_usable(self):
        self.assertEqual(self.build("")["projects"], [])
        self.assertEqual(self.build("## Intro\nText.\n")["categories"], [])
        result = self.build("## Empty\n| Project | Description |\n| --- | --- |\n")
        self.assertEqual(result["categories"], [{"id": "empty", "name": "Empty", "count": 0}])
        self.assertEqual(result["category_memberships"], 0)

    def test_duplicate_heading_anchors_follow_github_suffixes(self):
        result = self.build(self.source + "## AI & Language Models\n" + self.row)
        self.assertEqual([item["id"] for item in result["categories"]], ["ai--language-models", "ai--language-models-1"])
        result = self.build("## One\n" + self.row + "## One-1\n" + self.row + "## One\n" + self.row)
        self.assertEqual([item["id"] for item in result["categories"]], ["one", "one-1", "one-2"])

    def test_source_sha_is_explicit_full_and_normalized(self):
        self.assertEqual(self.build(source_sha="A" * 40)["source_sha"], "a" * 40)
        for sha in ("abcdef0", "g" * 40, "a" * 39, 123, "a" * 40 + "\n"):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                self.build(source_sha=sha)

    def test_snapshot_validation_is_reused(self):
        self.record["stargazers_count"] = True
        with self.assertRaises(ValueError):
            self.build()

    def test_checked_in_catalog_counts_and_all_memberships(self):
        root = catalog.ROOT
        source = (root / "README.source.md").read_text(encoding="utf-8")
        snapshot, alternatives, evidence = [json.loads((root / "data" / name).read_text(encoding="utf-8"))
                                            for name in ("github_metrics.json", "alternatives.json", "hn_evidence.json")]
        result = catalog.build_catalog(source, snapshot, alternatives, evidence)
        self.assertEqual(len(result["projects"]), 370)
        self.assertEqual(len(result["categories"]), 21)
        self.assertEqual(result["category_memberships"], 392)
        self.assertEqual(sum(len(item["categories"]) for item in result["projects"]), 392)
        self.assertEqual(sum(item["count"] for item in result["categories"]), 392)
        self.assertEqual(sum(bool(item["alternatives"]) for item in result["projects"]), 19)
        self.assertEqual(sum(item["hn"] is not None for item in result["projects"]), 15)
        by_url = {item["url"]: item for item in result["projects"]}
        for row in source.splitlines():
            match = catalog.readme.ENTRY.fullmatch(row)
            if match:
                self.assertIn(catalog.canonical_url(match[2]), by_url)
        self.assertEqual(len([item for item in result["projects"] if item["name"] == "OpenUI"]), 2)
        self.assertEqual(len([item for item in result["projects"] if item["name"] == "OpenPencil"]), 2)

    def test_cli_defaults_are_isolated_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "README.source.md").write_text(self.source, encoding="utf-8")
            (root / "README.md").write_text("Published README stays untouched\n", encoding="utf-8")
            for name, data in (("github_metrics", self.snapshot), ("alternatives", self.alternatives), ("hn_evidence", self.hn)):
                (root / "data" / (name + ".json")).write_text(json.dumps(data), encoding="utf-8")
            with patch.object(catalog, "ROOT", root), patch("sys.argv", ["build_catalog.py"]):
                catalog.main()
                first = (root / "tmp/site/catalog.json").read_bytes()
                catalog.main()
                self.assertEqual(first, (root / "tmp/site/catalog.json").read_bytes())
            self.assertEqual((root / "README.md").read_text(), "Published README stays untouched\n")
            self.assertEqual((root / "README.source.md").read_text(), self.source)
            self.assertEqual(json.loads(first), self.build())


if __name__ == "__main__":
    unittest.main()
