#!/usr/bin/env python3
"""Validate a built Galileo Extensions Pages artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_build_module():
    path = ROOT / "scripts/build_site.py"
    spec = importlib.util.spec_from_file_location("galileo_extensions_build_site", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CatalogTests(unittest.TestCase):
    site: Path

    @classmethod
    def setUpClass(cls) -> None:
        configured = getattr(cls, "configured_site", None)
        if configured is not None:
            cls.site = configured
            return
        cls._temporary = tempfile.TemporaryDirectory()
        cls.site = Path(cls._temporary.name) / "site"
        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "build_site.py"),
                "--output",
                str(cls.site),
            ],
            check=True,
            cwd=ROOT,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        temporary = getattr(cls, "_temporary", None)
        if temporary is not None:
            temporary.cleanup()

    def test_required_site_files_exist(self) -> None:
        for relative in [
            "index.html",
            "styles.css",
            "catalog.js",
            "catalog.json",
            ".nojekyll",
        ]:
            self.assertTrue((self.site / relative).is_file(), relative)
        self.assertFalse((self.site / "CNAME").exists())

    def test_public_page_has_accessible_contract_and_honest_boundaries(self) -> None:
        html = (self.site / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("<h1>"), 1)
        self.assertIn('href="#catalog"', html)
        self.assertIn('href="catalog.json"', html)
        self.assertIn("Review in Galileo", html)
        self.assertIn("Automatic installation", html)
        self.assertIn("background scripts", html.lower())
        self.assertNotIn("fully compatible", html.lower())

        catalog_js = (self.site / "catalog.js").read_text(encoding="utf-8")
        self.assertIn("servo:addons?catalog=", catalog_js)
        self.assertIn("encodeURIComponent(extension.id)", catalog_js)
        self.assertLess(
            catalog_js.index("Review in Galileo"),
            catalog_js.index("Download bundle"),
        )

    def test_catalog_archives_and_exact_digests(self) -> None:
        catalog = json.loads((self.site / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema_version"], 1)
        self.assertEqual(catalog["catalog_status"], "pre-alpha")
        self.assertTrue(
            re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", catalog["generated_at"]
            )
        )
        self.assertGreaterEqual(len(catalog["extensions"]), 1)
        for extension in catalog["extensions"]:
            archive_path = self.site / extension["download_url"]
            data = archive_path.read_bytes()
            self.assertEqual(
                hashlib.sha256(data).hexdigest(), extension["package_sha256"]
            )
            self.assertEqual(len(data), extension["package_bytes"])
            self.assertGreater(extension["rule_count"], 0)
            self.assertGreater(extension["content_style_count"], 0)
            self.assertGreater(extension["content_style_bytes"], 0)
            self.assertEqual(extension["install_mode"], "review-first-browser")
            self.assertEqual(set(extension["source_files"]), set(extension["files"]))
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(sorted(archive.namelist()), sorted(extension["files"]))
                for name, digest in extension["files"].items():
                    self.assertEqual(
                        hashlib.sha256(archive.read(name)).hexdigest(), digest
                    )
                    source_path = self.site / extension["source_files"][name]
                    self.assertTrue(source_path.is_file())
                    self.assertEqual(
                        hashlib.sha256(source_path.read_bytes()).hexdigest(), digest
                    )

    def test_preview_package_matches_galileo_static_runtime(self) -> None:
        manifest = json.loads(
            (ROOT / "extensions/galileo-tracker-shield/manifest.json").read_text()
        )
        rules = json.loads(
            (ROOT / "extensions/galileo-tracker-shield/rules.json").read_text()
        )
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["permissions"], ["declarativeNetRequest"])
        self.assertEqual(
            manifest["declarative_net_request"]["rule_resources"],
            [{"id": "tracker_shield_preview", "enabled": True, "path": "rules.json"}],
        )
        self.assertEqual(len({rule["id"] for rule in rules}), len(rules))
        self.assertTrue(all(rule["action"] == {"type": "block"} for rule in rules))
        self.assertTrue(
            all(
                "main_frame" not in rule["condition"]["resourceTypes"] for rule in rules
            )
        )
        self.assertEqual(
            manifest["content_scripts"],
            [
                {
                    "matches": ["<all_urls>"],
                    "css": ["content.css"],
                    "all_frames": True,
                    "run_at": "document_start",
                }
            ],
        )
        content_css = (
            ROOT / "extensions/galileo-tracker-shield/content.css"
        ).read_text()
        self.assertIn(".adsbygoogle", content_css)
        self.assertIn('iframe[src*="doubleclick.net"]', content_css)
        self.assertNotIn("@import", content_css.lower())
        self.assertNotIn("javascript", content_css.lower())

    def test_content_css_validator_fails_closed(self) -> None:
        build_site = load_build_module()
        source = ROOT / "extensions/galileo-tracker-shield"
        with tempfile.TemporaryDirectory() as temporary:
            extension = Path(temporary) / "galileo-tracker-shield"
            shutil.copytree(source, extension)

            manifest_path = extension / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["content_scripts"][0]["js"] = ["content.js"]
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "unsupported fields"):
                build_site.validate_manifest(
                    "galileo-tracker-shield", "0.2.0", extension
                )

            manifest["content_scripts"][0].pop("js")
            manifest["content_scripts"][0]["all_frames"] = 1
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "all_frames must be boolean"):
                build_site.validate_manifest(
                    "galileo-tracker-shield", "0.2.0", extension
                )

            manifest["content_scripts"][0]["all_frames"] = True
            manifest_path.write_text(json.dumps(manifest))
            (extension / "content.css").write_text(
                '@import url("https://example.test/a.css");'
            )
            with self.assertRaisesRegex(ValueError, "may not import remote styles"):
                build_site.validate_manifest(
                    "galileo-tracker-shield", "0.2.0", extension
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path)
    args, remaining = parser.parse_known_args()
    if args.site is not None:
        CatalogTests.configured_site = args.site.resolve()
    unittest.main(argv=[__file__, *remaining])


if __name__ == "__main__":
    main()
