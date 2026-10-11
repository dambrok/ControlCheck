"""
CSV Report Exporter
===================
Exports test suite outcomes to a tabular CSV format for downstream analysis,
spreadsheet inspection, and archival in engineering databases.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Union
from simuverify.runner import SuiteExecutionResult


def export_to_csv(result: SuiteExecutionResult, output_path: Union[str, Path]) -> Path:
    """Writes test results to a CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "Test_ID",
        "Test_Name",
        "Category",
        "Severity",
        "Status",
        "Execution_Time_ms",
        "Target_Speed_rad_s",
        "Actual_Speed_rad_s",
        "Speed_Error_rad_s",
        "Overshoot_Pct_Actual",
        "Overshoot_Pct_Limit",
        "Settling_Time_s_Actual",
        "Settling_Time_s_Limit",
        "Peak_Current_A_Actual",
        "Peak_Current_A_Limit",
        "Failure_Reasons",
        "Execution_Source",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for outcome in result.outcomes:
            metrics = outcome.actual_metrics
            expected = outcome.expected_values
            ac = outcome.acceptance_criteria

            writer.writerow(
                {
                    "Test_ID": outcome.test_id,
                    "Test_Name": outcome.name,
                    "Category": outcome.category,
                    "Severity": outcome.severity,
                    "Status": outcome.status,
                    "Execution_Time_ms": round(outcome.execution_time_ms, 2),
                    "Target_Speed_rad_s": expected.get("steady_state_speed", "N/A"),
                    "Actual_Speed_rad_s": metrics.get("steady_state_speed", "N/A"),
                    "Speed_Error_rad_s": metrics.get("steady_state_error", "N/A"),
                    "Overshoot_Pct_Actual": metrics.get("overshoot_pct", "N/A"),
                    "Overshoot_Pct_Limit": ac.get("max_overshoot_pct", "N/A"),
                    "Settling_Time_s_Actual": metrics.get("settling_time_s", "N/A"),
                    "Settling_Time_s_Limit": ac.get("max_settling_time_s", "N/A"),
                    "Peak_Current_A_Actual": metrics.get("peak_current_a", "N/A"),
                    "Peak_Current_A_Limit": ac.get("max_peak_current_a", "N/A"),
                    "Failure_Reasons": " | ".join(outcome.failure_reasons) if outcome.failure_reasons else "None",
                    "Execution_Source": outcome.source,
                }
            )

    return path
