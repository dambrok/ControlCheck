"""
Test Suite Execution Orchestrator
=================================
Coordinates test suite loading, model simulation execution, output validation,
performance metric aggregation, and report generation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from simuverify.config_loader import TestCaseConfig, TestSuiteConfig, load_test_suite
from simuverify.engine.simulator import DCMotorSimulator, SimulationResult
from simuverify.engine.validator import ResultValidator, TestOutcome


@dataclass
class SuiteExecutionResult:
    suite_name: str
    suite_version: str
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    pass_percentage: float
    total_duration_ms: float
    outcomes: List[TestOutcome]
    sim_traces: Dict[str, SimulationResult] = field(default_factory=dict)
    system_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "suite_version": self.suite_version,
            "timestamp": self.timestamp,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_tests": self.error_tests,
            "pass_percentage": round(self.pass_percentage, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "system_metadata": self.system_metadata,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }


class TestRunner:
    """
    Executes all configured test cases and decouples execution from validation.
    """
    __test__ = False

    def __init__(
        self,
        simulator: Optional[DCMotorSimulator] = None,
        validator: Optional[ResultValidator] = None,
    ):
        self.simulator = simulator or DCMotorSimulator()
        self.validator = validator or ResultValidator()

    def run_suite(
        self,
        suite: TestSuiteConfig | str | Path,
        on_progress: Optional[Callable[[int, int, TestCaseConfig, TestOutcome], None]] = None,
    ) -> SuiteExecutionResult:
        """
        Executes an entire test suite sequentially.
        """
        if isinstance(suite, (str, Path)):
            suite_config = load_test_suite(suite)
        else:
            suite_config = suite

        outcomes: List[TestOutcome] = []
        sim_traces: Dict[str, SimulationResult] = {}

        start_time_all = time.perf_counter()
        total = len(suite_config.test_cases)

        for idx, case in enumerate(suite_config.test_cases, start=1):
            t0 = time.perf_counter()
            sim_result: Optional[SimulationResult] = None
            exec_error: Optional[str] = None

            if case.is_valid:
                try:
                    sim_result = self.simulator.simulate(case.inputs)
                    sim_traces[case.id] = sim_result
                except Exception as exc:  # pylint: disable=broad-except
                    exec_error = f"{type(exc).__name__}: {str(exc)}"

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            outcome = self.validator.evaluate(
                test_case=case,
                sim_result=sim_result,
                exec_error=exec_error,
                exec_time_ms=elapsed_ms,
            )
            outcomes.append(outcome)

            if on_progress:
                on_progress(idx, total, case, outcome)

        total_duration_ms = (time.perf_counter() - start_time_all) * 1000.0

        passed_count = sum(1 for o in outcomes if o.status == "PASS")
        failed_count = sum(1 for o in outcomes if o.status == "FAIL")
        error_count = sum(1 for o in outcomes if o.status == "ERROR")
        pass_pct = (passed_count / total * 100.0) if total > 0 else 0.0

        timestamp_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        return SuiteExecutionResult(
            suite_name=suite_config.suite_name,
            suite_version=suite_config.version,
            timestamp=timestamp_iso,
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed_count,
            error_tests=error_count,
            pass_percentage=pass_pct,
            total_duration_ms=total_duration_ms,
            outcomes=outcomes,
            sim_traces=sim_traces,
            system_metadata=suite_config.system_under_test,
        )
