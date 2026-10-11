"""
Integration Tests for CLI Execution
"""

import subprocess
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_cli_execution_with_reports(tmp_path):
    config_file = PROJECT_ROOT / "config" / "test_cases.json"
    cli_script = PROJECT_ROOT / "scripts" / "run_simuverify.py"

    cmd = [
        sys.executable,
        str(cli_script),
        "--config",
        str(config_file),
        "--output-dir",
        str(tmp_path),
        "--format",
        "all",
        "--mode",
        "ci",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Verify output files
    assert (tmp_path / "validation_results.json").exists()
    assert (tmp_path / "validation_summary.csv").exists()
    assert (tmp_path / "validation_report.html").exists()
    assert (tmp_path / "plots").exists()


def test_cli_matlab_mode_reports_missing_cleanly():
    cli_script = PROJECT_ROOT / "scripts" / "run_simuverify.py"

    cmd = [
        sys.executable,
        str(cli_script),
        "--mode",
        "matlab",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    # If MATLAB is not installed, it returns 1 with clear explanation, never a traceback
    if "MATLAB NOT FOUND ON SYSTEM PATH" in result.stdout:
        assert result.returncode == 1
        assert "Traceback" not in result.stderr
