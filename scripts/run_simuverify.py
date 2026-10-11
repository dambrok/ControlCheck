"""
SimuVerify Command-Line Interface (CLI)
=======================================
Main entry point for executing automated test suites, validating dynamic models,
and generating validation reports in HTML, CSV, and JSON formats.

Usage:
  python scripts/run_simuverify.py --config config/test_cases.json --output-dir reports/
  python scripts/run_simuverify.py --mode ci --format all
  python scripts/run_simuverify.py --mode matlab
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simuverify.config_loader import TestCaseConfig, load_test_suite
from simuverify.engine.validator import TestOutcome
from simuverify.reporting.exporter_csv import export_to_csv
from simuverify.reporting.exporter_html import export_to_html
from simuverify.runner import SuiteExecutionResult, TestRunner


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SimuVerify: MATLAB/Simulink Automated Testing & Validation Framework",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=str(PROJECT_ROOT / "config" / "test_cases.json"),
        help="Path to test suite configuration file (JSON or YAML)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "reports"),
        help="Directory where generated reports and plots will be stored",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="all",
        choices=["all", "html", "csv", "json"],
        help="Report export format",
    )
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        default="ci",
        choices=["ci", "matlab"],
        help="Execution mode: 'ci' for standalone deterministic Python engine, or 'matlab' for native MATLAB batch runner",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed console output for each criterion check",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 if any test fails (useful in CI pipelines requiring 100% pass rate)",
    )
    return parser.parse_args()


def run_matlab_mode(config_path: Path, output_dir: Path) -> int:
    """Invokes MATLAB in batch mode if installed on the system."""
    matlab_exe = shutil.which("matlab")
    if not matlab_exe:
        print("\n" + "=" * 70)
        print("[-] MATLAB NOT FOUND ON SYSTEM PATH")
        print("=" * 70)
        print("To run tests in native MATLAB mode:")
        print("  1. Ensure MathWorks MATLAB R2020b or newer is installed.")
        print("  2. Add the MATLAB bin directory to your system PATH.")
        print("  3. Or launch MATLAB directly and execute: ")
        print("     >> addpath(genpath('matlab'))")
        print("     >> run_all_tests")
        print("\nNotice: In standard CI environments or when MATLAB is absent,")
        print("use the deterministic engine via: python scripts/run_simuverify.py --mode ci\n")
        return 1

    print(f"\n[*] Found MATLAB at: {matlab_exe}")
    print("[*] Launching MATLAB batch runner...")
    matlab_cmd = (
        f"addpath(genpath('{PROJECT_ROOT / 'matlab'}')); "
        f"run_all_tests('{config_path}', '{output_dir}'); exit;"
    )
    try:
        proc = subprocess.run(
            [matlab_exe, "-batch", matlab_cmd],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        print(proc.stdout)
        return 0
    except subprocess.CalledProcessError as err:
        print(f"[-] MATLAB execution failed with code {err.returncode}:")
        print(err.stderr)
        return err.returncode


def print_banner(mode: str, config_path: str):
    print("=" * 75)
    print("  SIMUVERIFY: Automated Testing & Validation Framework")
    print("=" * 75)
    print(f"  Configuration : {config_path}")
    print(f"  Execution Mode: {mode.upper()} ({'Deterministic Python Engine' if mode == 'ci' else 'MathWorks MATLAB'})")
    print("=" * 75)


def print_progress(idx: int, total: int, case: TestCaseConfig, outcome: TestOutcome, verbose: bool):
    status_symbols = {
        "PASS": "[PASS]",
        "FAIL": "[FAIL]",
        "ERROR": "[ERROR]",
    }
    sym = status_symbols.get(outcome.status, outcome.status)
    print(f" [{idx:02d}/{total:02d}] {sym:<7} {outcome.test_id:<11} {case.name[:36]:<36} ({outcome.execution_time_ms:6.2f} ms)")

    if verbose or outcome.status != "PASS":
        if outcome.actual_metrics:
            w_act = outcome.actual_metrics.get("steady_state_speed", "N/A")
            os_act = outcome.actual_metrics.get("overshoot_pct", "N/A")
            ts_act = outcome.actual_metrics.get("settling_time_s", "N/A")
            i_act = outcome.actual_metrics.get("peak_current_a", "N/A")
            print(f"         |-- Measured: Speed={w_act} rad/s | Overshoot={os_act}% | Settling={ts_act}s | Current={i_act}A")
        if outcome.failure_reasons:
            for r in outcome.failure_reasons:
                print(f"         |-- Reason: {r}")


def main() -> int:
    args = parse_arguments()
    config_path = Path(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print_banner(args.mode, str(config_path))

    if args.mode == "matlab":
        return run_matlab_mode(config_path, output_dir)

    # 1. Load configuration
    try:
        suite = load_test_suite(config_path)
    except Exception as exc:
        print(f"[-] Fatal error loading configuration: {exc}")
        return 2

    # 2. Execute test runner
    runner = TestRunner()

    def progress_callback(idx: int, total: int, case: TestCaseConfig, outcome: TestOutcome):
        print_progress(idx, total, case, outcome, args.verbose)

    result = runner.run_suite(suite, on_progress=progress_callback)

    # 3. Export reports
    export_formats = {"html", "csv", "json"} if args.format == "all" else {args.format}

    print("\n[*] Exporting validation artifacts:")
    if "json" in export_formats:
        json_path = output_dir / "validation_results.json"
        json_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(f"  [+] JSON Data   : {json_path}")

    if "csv" in export_formats:
        csv_path = output_dir / "validation_summary.csv"
        export_to_csv(result, csv_path)
        print(f"  [+] CSV Summary : {csv_path}")

    if "html" in export_formats:
        html_path = output_dir / "validation_report.html"
        plots_dir = output_dir / "plots"
        export_to_html(result, html_path, plots_dir=plots_dir)
        print(f"  [+] HTML Report : {html_path}")

    # 4. Print Summary
    print("\n" + "=" * 75)
    print("  VERIFICATION SUITE SUMMARY")
    print("=" * 75)
    print(f"  Total Scenarios Executed : {result.total_tests}")
    print(f"  Passed (Within Limits)   : {result.passed_tests}")
    print(f"  Failed (Tolerance Breach): {result.failed_tests} (e.g. TC-FLT-01 motor stall, TC-FLT-02 gain overshoot)")
    print(f"  Configuration / Errors   : {result.error_tests} (e.g. TC-ERR-01 negative time, TC-ERR-02 missing key)")
    print(f"  Pass Rate                : {result.pass_percentage:.1f}%")
    print(f"  Total Execution Duration : {result.total_duration_ms:.2f} ms")
    print("=" * 75 + "\n")

    if args.strict and (result.failed_tests > 0 or result.error_tests > 0):
        print("[-] Exiting with failure status code 1 (--strict enabled).")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
