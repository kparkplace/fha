from __future__ import annotations

import unittest
from unittest.mock import patch

from dash import html

import app


def _reset_cache() -> None:
    app.DATA_CACHE["capratio_df"] = None
    app.DATA_CACHE["claims_df"] = None
    app.DATA_CACHE["creditrisk_df"] = None
    app.DATA_CACHE["creditsubsidy_df"] = None
    app.DATA_CACHE["endorsements_df"] = None
    app.DATA_CACHE["loanlimits_df"] = None
    app.DATA_CACHE["loaded_at"] = None
    app.DATA_CACHE["load_error"] = None
    app.DATA_CACHE["creditsubsidy_error"] = None


class TestAppSmoke(unittest.TestCase):
    def setUp(self) -> None:
        _reset_cache()

    def tearDown(self) -> None:
        _reset_cache()

    def test_healthz(self) -> None:
        body, status = app.healthz()
        self.assertEqual(body, "ok")
        self.assertEqual(status, 200)

    def test_ensure_data_loaded_populates_core_datasets(self) -> None:
        app.DATA_CACHE["creditsubsidy_error"] = "skip network in test"
        app.ensure_data_loaded()

        self.assertIsNone(app.DATA_CACHE["load_error"])
        self.assertIsNotNone(app.DATA_CACHE["capratio_df"])
        self.assertIsNotNone(app.DATA_CACHE["claims_df"])
        self.assertIsNotNone(app.DATA_CACHE["creditrisk_df"])
        self.assertIsNotNone(app.DATA_CACHE["endorsements_df"])
        self.assertIsNotNone(app.DATA_CACHE["loanlimits_df"])
        self.assertIsNotNone(app.DATA_CACHE["loaded_at"])

    def test_build_dashboard_sections_has_expected_section_ids(self) -> None:
        app.DATA_CACHE["creditsubsidy_error"] = "skip network in test"
        app.ensure_data_loaded()

        sections_wrapper = app.build_dashboard_sections()
        self.assertIsInstance(sections_wrapper, html.Div)
        self.assertIsInstance(sections_wrapper.children, list)

        ids = [child.id for child in sections_wrapper.children if hasattr(child, "id")]
        self.assertIn("section-originations", ids)
        self.assertIn("section-loanlimits", ids)
        self.assertIn("section-credit-risk", ids)
        self.assertIn("section-claim-rates", ids)
        self.assertIn("section-mmi-capital", ids)


class TestLoadAndRenderCallback(unittest.TestCase):
    def setUp(self) -> None:
        _reset_cache()

    def tearDown(self) -> None:
        _reset_cache()

    def test_load_and_render_error_path(self) -> None:
        app.DATA_CACHE["load_error"] = "Missing parquet input"

        with patch.object(app, "ensure_data_loaded", return_value=None):
            status_children, status_style, summary_children, sections_children = app.load_and_render(0)

        self.assertTrue(isinstance(status_children, list))
        self.assertEqual(status_style.get("backgroundColor"), "#fef2f2")
        self.assertIsInstance(summary_children, list)
        self.assertEqual(sections_children, [])

    def test_load_and_render_warning_path(self) -> None:
        app.DATA_CACHE["load_error"] = None
        app.DATA_CACHE["creditsubsidy_error"] = "Credit subsidy unavailable"
        expected_sections = html.Div("sections")
        expected_stats = [html.Li("x")]

        with (
            patch.object(app, "ensure_data_loaded", return_value=None),
            patch.object(app, "build_dashboard_sections", return_value=expected_sections),
            patch.object(app, "render_stats_items", return_value=expected_stats),
        ):
            status_children, status_style, summary_children, sections_children = app.load_and_render(0)

        self.assertTrue(isinstance(status_children, list))
        self.assertEqual(status_style.get("backgroundColor"), "#fffbeb")
        self.assertEqual(summary_children, expected_stats)
        self.assertEqual(sections_children, expected_sections)

    def test_load_and_render_success_path(self) -> None:
        app.DATA_CACHE["load_error"] = None
        app.DATA_CACHE["creditsubsidy_error"] = None
        expected_sections = html.Div("sections")
        expected_stats = [html.Li("x")]

        with (
            patch.object(app, "ensure_data_loaded", return_value=None),
            patch.object(app, "build_dashboard_sections", return_value=expected_sections),
            patch.object(app, "render_stats_items", return_value=expected_stats),
        ):
            status_children, status_style, summary_children, sections_children = app.load_and_render(0)

        self.assertEqual(status_children, "Data loaded successfully.")
        self.assertEqual(status_style.get("backgroundColor"), "#ecfdf3")
        self.assertEqual(summary_children, expected_stats)
        self.assertEqual(sections_children, expected_sections)


if __name__ == "__main__":
    unittest.main()
