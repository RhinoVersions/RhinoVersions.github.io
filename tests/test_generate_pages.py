import datetime as dt
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path to allow import
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import generate_pages as gp

# A slice of data/rhino-versions-all.md covering every filename convention.
SAMPLE_MD = """\
    - [rhino_9.0.26272.12303.exe](https://files.mcneel.com/dujour/exe/20260929/rhino_9.0.26272.12303.exe)
    - [rhino_wip_9.0.26167.11546.dmg](https://files.mcneel.com/rhino/9/mac/releases/rhino_wip_9.0.26167.11546.dmg)
    - [rhino_9.0.26167.11545.exe](https://files.mcneel.com/dujour/exe/20260616/rhino_9.0.26167.11545.exe)
    - [rhino_8.18.25098.11002.dmg](https://files.mcneel.com/rhino/8/mac/releases/rhino_8.18.25098.11002.dmg)
    - [rhino_en-us_8.18.25098.11001.exe](https://files.mcneel.com/dujour/exe/20250408/rhino_en-us_8.18.25098.11001.exe)
    - [rhino_8.17.25066.07002.dmg](https://files.mcneel.com/rhino/8/mac/releases/rhino_8.17.25066.07002.dmg)
    - [rhino_en-us_8.17.25066.07001.exe](https://files.mcneel.com/dujour/exe/20250307/rhino_en-us_8.17.25066.07001.exe)
    - [rhino_de-de_8.17.25066.07001.exe](https://files.mcneel.com/dujour/exe/20250307/rhino_de-de_8.17.25066.07001.exe)
    - [rhino_zh-tw_8.17.25066.07001.exe](https://files.mcneel.com/dujour/exe/20250307/rhino_zh-tw_8.17.25066.07001.exe)
    - [rhino_en-us_8.0.23304.09001.exe](https://files.mcneel.com/dujour/exe/20231031/rhino_en-us_8.0.23304.09001.exe)
    - [rhino_en-us_6.35.21222.17001.exe](https://files.mcneel.com/dujour/exe/20210810/rhino_en-us_6.35.21222.17001.exe)
"""


class GeneratePagesTests(unittest.TestCase):
    def setUp(self):
        self.builds = gp.load_builds(SAMPLE_MD)
        self.by_key = {b.key: b for b in self.builds}

    def test_parse_installer_filename_conventions(self):
        win = gp.parse_installer("rhino_en-us_8.17.25066.07001.exe", "https://example.test/a.exe")
        self.assertEqual((win.platform, win.locale, win.version), ("windows", "en-us", "8.17.25066.07001"))

        multi = gp.parse_installer("rhino_9.0.26272.12303.exe", "https://example.test/b.exe")
        self.assertEqual((multi.platform, multi.locale), ("windows", "multi"))

        mac = gp.parse_installer("rhino_8.17.25066.07002.dmg", "https://example.test/c.dmg")
        self.assertEqual((mac.platform, mac.locale), ("mac", "multi"))

        wip_mac = gp.parse_installer("rhino_wip_9.0.26167.11546.dmg", "https://example.test/d.dmg")
        self.assertEqual((wip_mac.platform, wip_mac.locale, wip_mac.version), ("mac", "multi", "9.0.26167.11546"))

    def test_parse_installer_rejects_unexpected_input(self):
        self.assertIsNone(gp.parse_installer("rhino_8.17.dmg", "https://example.test/x.dmg"))
        self.assertIsNone(gp.parse_installer("notes.txt", "https://example.test/notes.txt"))
        self.assertIsNone(gp.parse_installer("rhino_8.17.25066.07002.dmg", "javascript:alert(1)"))

    def test_load_builds_groups_windows_and_mac_by_build_day(self):
        self.assertEqual(
            [b.key for b in self.builds],
            ["9.0.26272", "9.0.26167", "8.18.25098", "8.17.25066", "8.0.23304", "6.35.21222"],
        )
        build = self.by_key["8.17.25066"]
        self.assertEqual(build.windows_version, "8.17.25066.07001")
        self.assertEqual(build.mac_version, "8.17.25066.07002")
        self.assertEqual(build.date, dt.date(2025, 3, 7))
        # English first, then the configured locale order.
        self.assertEqual([i.locale for i in build.windows], ["en-us", "de-de", "zh-tw"])
        self.assertEqual(build.path, "/rhino/8/8.17.25066/")

    def test_load_builds_keeps_newest_installer_per_language(self):
        md = SAMPLE_MD + (
            "    - [rhino_en-us_8.17.25066.09001.exe](https://files.mcneel.com/dujour/exe/20250307/"
            "rhino_en-us_8.17.25066.09001.exe)\n"
        )
        build = {b.key: b for b in gp.load_builds(md)}["8.17.25066"]
        self.assertEqual(build.windows[0].version, "8.17.25066.09001")
        self.assertEqual(len([i for i in build.windows if i.locale == "en-us"]), 1)

    def test_decode_build_date_and_nuget_version(self):
        self.assertEqual(gp.decode_build_date("25066"), dt.date(2025, 3, 7))
        self.assertEqual(gp.decode_build_date("24366"), dt.date(2024, 12, 31))  # leap year
        self.assertEqual(gp.nuget_version("8.17.25066.07001"), "8.17.25066.7001")

    def test_release_labels(self):
        self.assertEqual(gp.release_label(self.by_key["8.17.25066"]), "Rhino 8 SR17")
        self.assertEqual(gp.release_label(self.by_key["8.0.23304"]), "Rhino 8 initial release")
        self.assertEqual(gp.release_label(self.by_key["9.0.26272"]), "Rhino 9 Early Preview")

    def test_build_title_names_exact_versions(self):
        self.assertEqual(
            gp.build_title(self.by_key["8.17.25066"]),
            "Rhino 8.17.25066.07001 (Windows) & 8.17.25066.07002 (Mac) Download – Rhino 8 SR17",
        )
        self.assertEqual(
            gp.build_title(self.by_key["9.0.26272"]),
            "Rhino 9.0.26272.12303 Download for Windows – Rhino 9 Early Preview",
        )

    def test_build_page_is_crawlable_without_javascript(self):
        files = gp.render_site(self.builds)
        page = files["rhino/8/8.17.25066/index.html"]

        title = re.search(r"<title>(.*?)</title>", page).group(1)
        self.assertIn("8.17.25066.07002", title)
        self.assertIn("8.17.25066.07001", title)
        self.assertIn('<link rel="canonical" href="https://rhinoversions.github.io/rhino/8/8.17.25066/">', page)
        self.assertIn('href="https://files.mcneel.com/rhino/8/mac/releases/rhino_8.17.25066.07002.dmg"', page)
        self.assertIn(">rhino_de-de_8.17.25066.07001.exe</a>", page)
        self.assertIn("https://www.nuget.org/packages/RhinoCommon/8.17.25066.7001", page)
        # Pager links to the neighbouring builds of the same major.
        self.assertIn('href="/rhino/8/8.0.23304/"', page)
        self.assertIn('href="/rhino/8/8.18.25098/"', page)
        self.assertNotIn("<script src=", page)

    def test_prerelease_page_has_no_nuget_link(self):
        page = gp.render_site(self.builds)["rhino/9/9.0.26167/index.html"]
        self.assertNotIn("nuget.org/packages/RhinoCommon/9.", page)
        self.assertIn("Latest Rhino 9 Early Preview build", gp.render_site(self.builds)["rhino/9/9.0.26272/index.html"])

    def test_major_and_archive_pages_link_every_build(self):
        files = gp.render_site(self.builds)
        rhino8 = files["rhino/8/index.html"]
        for key in ("8.18.25098", "8.17.25066", "8.0.23304"):
            self.assertIn(f'href="/rhino/8/{key}/"', rhino8)
        self.assertIn(">8.17.25066.07002</a>", rhino8)
        archive = files["rhino/index.html"]
        for major in ("9", "8", "6"):
            self.assertIn(f'href="/rhino/{major}/"', archive)

    def test_sitemap_lists_every_page(self):
        files = gp.render_site(self.builds)
        locs = re.findall(r"<loc>(.*?)</loc>", files["sitemap.xml"])
        self.assertEqual(locs[0], "https://rhinoversions.github.io/")
        self.assertIn("https://rhinoversions.github.io/rhino/8/8.17.25066/", locs)
        self.assertIn("<lastmod>2025-03-07</lastmod>", files["sitemap.xml"])
        pages = [rel for rel in files if rel.endswith("index.html")]
        self.assertEqual(len(locs), len(pages) + 1)  # + the dashboard

    def test_output_is_escaped(self):
        md = '    - [rhino_en-us_8.17.25066.07001.exe](https://example.test/a"onmouseover="x.exe)\n'
        page = gp.render_site(gp.load_builds(md))["rhino/8/8.17.25066/index.html"]
        self.assertIn('href="https://example.test/a&quot;onmouseover=&quot;x.exe"', page)
        self.assertNotIn('a"onmouseover', page)

    def test_write_site_writes_and_prunes_stale_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = root / "rhino" / "8" / "8.1.23325" / "index.html"
            stale.parent.mkdir(parents=True)
            stale.write_text("old", encoding="utf-8")
            keep = root / "rhino" / "notes.txt"
            keep.write_text("not generated", encoding="utf-8")

            files = gp.render_site(self.builds)
            changed = gp.write_site(str(root), files)

            self.assertEqual(changed, len(files) + 1)  # every file + the pruned page
            self.assertFalse(stale.parent.exists())
            self.assertTrue(keep.exists())
            self.assertTrue((root / "rhino" / "8" / "8.17.25066" / "index.html").exists())
            self.assertTrue((root / "sitemap.xml").exists())

            # Rerunning with the same data changes nothing.
            self.assertEqual(gp.write_site(str(root), files), 0)

    def test_main_refuses_to_wipe_pages_for_empty_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "empty.md"
            data.write_text("", encoding="utf-8")
            with self.assertRaises(SystemExit):
                gp.main(["--data", str(data), "--root", tmp])
            self.assertFalse((Path(tmp) / "rhino").exists())


if __name__ == "__main__":
    unittest.main()
