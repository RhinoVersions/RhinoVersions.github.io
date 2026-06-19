import datetime as dt
import sys
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Keep tests self-contained even if requests isn't installed.
if "requests" not in sys.modules:
    sys.modules["requests"] = SimpleNamespace(
        get=lambda *args, **kwargs: None,
        head=lambda *args, **kwargs: None,
        RequestException=Exception,
    )

# Add scripts directory to path to allow import
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import fetch_versions as fv


class FetchVersionsTests(unittest.TestCase):
    def test_list_stable_for_majors_filters_and_sorts(self):
        all_versions = [
            "8.24.25281.15001",
            "8.24.25282.10001",
            "7.31.25281.15001",
            "8.24.25281.15001-beta",
            "6.10.20100.10001",
        ]

        stable = fv.list_stable_for_majors(all_versions, [7, 8])

        self.assertEqual(
            stable,
            ["8.24.25282.10001", "8.24.25281.15001", "7.31.25281.15001"],
        )

    def test_decode_version_date(self):
        # yyddd = 25281 -> 2025 day 281 = 2025-10-08
        date = fv.decode_version_date("8.24.25281.15001")
        self.assertEqual(date, dt.date(2025, 10, 8))

    def test_build_windows_url(self):
        date = dt.date(2025, 10, 8)
        url = fv.build_windows_url("8.24.25281.15001", date, "en-us")
        self.assertEqual(
            url,
            "https://files.mcneel.com/dujour/exe/20251008/rhino_en-us_8.24.25281.15001.exe",
        )

    def test_build_mac_url_candidates(self):
        urls = fv.build_mac_url_candidates("8.25.25328.11001")
        self.assertEqual(
            urls,
            [
                "https://files.mcneel.com/rhino/8/mac/releases/rhino_8.25.25328.11001.dmg",
                "https://files.mcneel.com/rhino/8/mac/releases/rhino_8.25.25328.11002.dmg",
            ],
        )

    @patch("fetch_versions.requests.get")
    def test_versions_from_registration_fetches_nested_pages(self, mock_get):
        page_response = Mock()
        page_response.raise_for_status.return_value = None
        page_response.json.return_value = {
            "items": [
                {"catalogEntry": {"version": "8.24.25281.15001"}},
                {"catalogEntry": {"version": "7.31.25281.15001"}},
            ]
        }
        mock_get.return_value = page_response

        reg_json = {"items": [{"@id": "https://example.test/page-1.json", "items": None}]}

        versions = fv.versions_from_registration(reg_json)

        self.assertEqual(versions, ["8.24.25281.15001", "7.31.25281.15001"])
        mock_get.assert_called_once()

    def test_prepend_latest_and_write_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_latest = Path(tmp) / "latest.md"
            md_all = Path(tmp) / "all.md"

            changed = fv.prepend_latest(
                str(md_latest),
                "rhino_en-us_8.24.25281.15001.exe",
                "https://files.mcneel.com/dujour/exe/20251008/rhino_en-us_8.24.25281.15001.exe",
            )
            self.assertTrue(changed)

            # Duplicate should not be added again
            changed_again = fv.prepend_latest(
                str(md_latest),
                "rhino_en-us_8.24.25281.15001.exe",
                "https://files.mcneel.com/dujour/exe/20251008/rhino_en-us_8.24.25281.15001.exe",
            )
            self.assertFalse(changed_again)

            count = fv.write_all(
                str(md_all),
                [
                    ("rhino_en-us_8.24.25281.15001.exe", "https://example.test/win.exe"),
                    ("rhino_8.24.25281.15002.dmg", "https://example.test/mac.dmg"),
                ],
            )
            self.assertEqual(count, 2)
            self.assertTrue(md_all.read_text(encoding="utf-8").strip().startswith("- [rhino_en-us_8.24.25281.15001.exe]"))

    @patch("fetch_versions.fetch_registration_index")
    @patch("fetch_versions.versions_from_registration")
    @patch("fetch_versions.list_stable_for_majors")
    def test_get_stable_versions_orchestration(self, mock_list_stable, mock_versions_from_reg, mock_fetch_reg):
        mock_fetch_reg.return_value = {"some": "data"}
        mock_versions_from_reg.return_value = ["v1", "v2"]
        mock_list_stable.return_value = ["v1"]

        stable = fv.get_stable_versions()

        mock_fetch_reg.assert_called_once()
        mock_versions_from_reg.assert_called_once_with({"some": "data"})
        mock_list_stable.assert_called_once_with(["v1", "v2"], fv.MAJORS)
        self.assertEqual(stable, ["v1"])

    def test_version_for_filename(self):
        # Valid 4-part version (already padded)
        self.assertEqual(fv._version_for_filename("8.24.25281.15001"), "8.24.25281.15001")
        # Valid 4-part version (needs padding)
        self.assertEqual(fv._version_for_filename("8.24.1.2"), "8.24.00001.00002")
        # Prerelease suffix is dropped (installer filename has no -wip)
        self.assertEqual(fv._version_for_filename("9.0.26097.12305-wip"), "9.0.26097.12305")
        # Invalid version (fewer than 4 parts)
        with self.assertRaises(ValueError) as cm:
            fv._version_for_filename("1.2.3")
        self.assertEqual(str(cm.exception), "Unexpected version: 1.2.3")

    def test_is_prerelease(self):
        self.assertTrue(fv.is_prerelease("9.0.26097.12305-wip"))
        self.assertFalse(fv.is_prerelease("8.24.25281.15001"))

    def test_parse_version_tuple_ignores_prerelease_suffix(self):
        self.assertEqual(fv.parse_version_tuple("9.0.26097.12305-wip"), (9, 0, 26097, 12305))
        self.assertEqual(fv.parse_version_tuple("8.24.25281.15001"), (8, 24, 25281, 15001))

    def test_list_stable_includes_wip_only_for_prerelease_majors(self):
        all_versions = [
            "9.0.26097.12305-wip",
            "9.0.26083.12305-wip",
            "8.32.26160.13001",
            "8.32.26160.13001-beta",  # stable major -> beta excluded
            "7.31.25281.15001",
        ]
        result = fv.list_stable_for_majors(all_versions, [7, 8, 9])
        # WIP builds kept for major 9, sorted with everything else (desc).
        self.assertEqual(
            result,
            [
                "9.0.26097.12305-wip",
                "9.0.26083.12305-wip",
                "8.32.26160.13001",
                "7.31.25281.15001",
            ],
        )

    def test_list_stable_excludes_rc_dujour_beta_for_v6(self):
        all_versions = [
            "6.35.21222.17001",       # stable -> keep
            "6.32.20337.13001-rc",    # rc -> drop
            "6.26.20119.290-dujour",  # dujour -> drop
            "6.0.18016.23451",        # stable -> keep
            "6.0.16257.3161-wip",     # wip (major 6 not a prerelease major) -> drop
        ]
        result = fv.list_stable_for_majors(all_versions, [6])
        self.assertEqual(result, ["6.35.21222.17001", "6.0.18016.23451"])

    def test_resolve_mac_url_picks_plus_one(self):
        # Exact 404, +1 200 -> returns the +1 URL.
        with patch("fetch_versions.url_exists", side_effect=lambda u: u.endswith("17002.dmg")):
            url = fv.resolve_mac_url("6.35.21222.17001")
        self.assertEqual(
            url,
            "https://files.mcneel.com/rhino/6/mac/releases/rhino_6.35.21222.17002.dmg",
        )

    def test_resolve_mac_url_returns_none_when_absent(self):
        with patch("fetch_versions.url_exists", return_value=False):
            self.assertIsNone(fv.resolve_mac_url("6.0.18016.23451"))

    def test_resolve_mac_urls_only_includes_found(self):
        # Found for 8.x (+1), absent for 6.0.
        def fake_exists(u):
            return "8.32.26160.13002.dmg" in u
        with patch("fetch_versions.url_exists", side_effect=fake_exists):
            result = fv.resolve_mac_urls(["8.32.26160.13001", "6.0.18016.23451"])
        self.assertEqual(
            result,
            {"8.32.26160.13001": "https://files.mcneel.com/rhino/8/mac/releases/rhino_8.32.26160.13002.dmg"},
        )

    def test_resolve_prerelease_windows_prefers_multilingual(self):
        # Multilingual candidate exists -> returned (no-locale form).
        def fake_exists(u):
            return u.endswith("rhino_9.0.26167.11545.exe")
        with patch("fetch_versions.url_exists", side_effect=fake_exists):
            url = fv.resolve_prerelease_windows_url("9.0.26167.11545-wip")
        self.assertEqual(
            url,
            "https://files.mcneel.com/dujour/exe/20260616/rhino_9.0.26167.11545.exe",
        )

    def test_resolve_prerelease_windows_falls_back_to_locale(self):
        # Only the locale-specific (older WIP) form exists.
        def fake_exists(u):
            return u.endswith("rhino_en-us_9.0.26097.12305.exe")
        with patch("fetch_versions.url_exists", side_effect=fake_exists):
            url = fv.resolve_prerelease_windows_url("9.0.26097.12305-wip")
        self.assertTrue(url.endswith("rhino_en-us_9.0.26097.12305.exe"))

    def test_resolve_prerelease_windows_none_when_absent(self):
        with patch("fetch_versions.url_exists", return_value=False):
            self.assertIsNone(fv.resolve_prerelease_windows_url("9.0.26167.11545-wip"))

    def test_build_windows_url_strips_wip(self):
        # Day 097 of 2026 -> 2026-04-07
        date = fv.decode_version_date("9.0.26097.12305-wip")
        url = fv.build_windows_url("9.0.26097.12305-wip", date, "en-us")
        self.assertEqual(
            url,
            "https://files.mcneel.com/dujour/exe/20260407/rhino_en-us_9.0.26097.12305.exe",
        )


if __name__ == "__main__":
    unittest.main()
