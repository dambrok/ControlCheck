"""
Unit Tests for CSV, HTML, and Plot Reporting Modules
"""

import csv
from pathlib import Path
import pytest
from simuverify.config_loader import load_test_suite
from simuverify.reporting.exporter_csv import export_to_csv
from simuverify.reporting.exporter_html import export_to_html
from simuverify.reporting.plotter import generate_all_plots
from simuverify.runner import TestRunner

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def executed_suite():
    config_file = PROJECT_ROOT / "config" / "test_cases.json"
    suite = load_test_suite(config_file)
    runner = TestRunner()
    return runner.run_suite(suite)


def test_export_to_csv(executed_suite, tmp_path):
    csv_file = tmp_path / "summary.csv"
    res_path = export_to_csv(executed_suite, csv_file)

    assert res_path.exists()
    assert res_path.stat().st_size > 0

    with open(res_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == executed_suite.total_tests
    assert "Test_ID" in rows[0]
    assert "Status" in rows[0]


def test_export_to_html(executed_suite, tmp_path):
    html_file = tmp_path / "report.html"
    plots_dir = tmp_path / "plots"
    res_path = export_to_html(executed_suite, html_file, plots_dir=plots_dir)

    assert res_path.exists()
    content = res_path.read_text(encoding="utf-8")

    assert "<!DOCTYPE html>" in content
    assert "SimuVerify" in content
    assert "Automated Testing &amp; Validation Report" in content or "Automated Testing & Validation Report" in content
    assert executed_suite.suite_name in content
    assert str(executed_suite.passed_tests) in content


def test_generate_all_plots(executed_suite, tmp_path):
    plots_dir = tmp_path / "plots"
    outcome_map = {o.test_id: o for o in executed_suite.outcomes}
    encoded = generate_all_plots(executed_suite.sim_traces, outcome_map, plots_dir)

    assert len(encoded) > 0
    # Check that PNG files exist on disk
    png_files = list(plots_dir.glob("*.png"))
    assert len(png_files) > 0
