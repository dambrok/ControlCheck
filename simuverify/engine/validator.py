"""
Verification and Failure Analysis Engine
========================================
Compares simulation outputs against formal acceptance limits and tolerances.
Performs root-cause analysis on failures and records diagnostics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from simuverify.config_loader import TestCaseConfig
from simuverify.engine.simulator import SimulationResult


@dataclass
class CriterionCheck:
    criterion_name: str
    expected_rule: str
    actual_value: Any
    passed: bool
    message: str


@dataclass
class TestOutcome:
    __test__ = False
    test_id: str
    name: str
    category: str
    severity: str
    status: str  # "PASS" | "FAIL" | "ERROR"
    execution_time_ms: float
    actual_metrics: Dict[str, Any]
    expected_values: Dict[str, Any]
    acceptance_criteria: Dict[str, Any]
    criterion_checks: List[CriterionCheck] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)
    source: str = "SimuVerify Deterministic Python Engine (CI Mode)"

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "category": self.category,
            "severity": self.severity,
            "status": self.status,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "actual_metrics": self.actual_metrics,
            "expected_values": self.expected_values,
            "acceptance_criteria": self.acceptance_criteria,
            "failure_reasons": self.failure_reasons,
            "source": self.source,
            "criterion_checks": [
                {
                    "criterion": c.criterion_name,
                    "rule": c.expected_rule,
                    "actual": c.actual_value,
                    "passed": c.passed,
                    "message": c.message,
                }
                for c in self.criterion_checks
            ],
        }


class ResultValidator:
    """
    Evaluates dynamic system outputs against acceptance tolerances.
    """

    def evaluate(
        self,
        test_case: TestCaseConfig,
        sim_result: Optional[SimulationResult],
        exec_error: Optional[str] = None,
        exec_time_ms: float = 0.0,
    ) -> TestOutcome:
        """
        Conducts multi-point acceptance analysis for a test case.
        """
        # If configuration had fatal validation issues or execution failed
        if not test_case.is_valid:
            fatal_msgs = [f"{iss.field}: {iss.message}" for iss in test_case.issues if iss.is_fatal]
            return TestOutcome(
                test_id=test_case.id,
                name=test_case.name,
                category=test_case.category,
                severity=test_case.severity,
                status="ERROR",
                execution_time_ms=exec_time_ms,
                actual_metrics={},
                expected_values=test_case.expected,
                acceptance_criteria=test_case.acceptance_criteria,
                failure_reasons=[f"Invalid Test Configuration: {', '.join(fatal_msgs)}"],
            )

        if exec_error is not None or sim_result is None:
            return TestOutcome(
                test_id=test_case.id,
                name=test_case.name,
                category=test_case.category,
                severity=test_case.severity,
                status="ERROR",
                execution_time_ms=exec_time_ms,
                actual_metrics={},
                expected_values=test_case.expected,
                acceptance_criteria=test_case.acceptance_criteria,
                failure_reasons=[f"Execution Exception: {exec_error or 'Simulation produced no output'}"],
            )

        metrics = sim_result.metrics
        expected = test_case.expected
        ac = test_case.acceptance_criteria

        checks: List[CriterionCheck] = []
        reasons: List[str] = []

        # 1. Steady-state speed absolute tolerance
        if "speed_tolerance_abs" in ac and "steady_state_speed" in expected:
            target = float(expected["steady_state_speed"])
            tol = float(ac["speed_tolerance_abs"])
            actual = float(metrics.get("steady_state_speed", float("nan")))
            diff = abs(actual - target)
            passed = diff <= tol
            msg = f"|{actual:.2f} - {target:.2f}| = {diff:.2f} (limit <= {tol:.2f} rad/s)"
            checks.append(CriterionCheck("speed_tolerance_abs", f"diff <= {tol:.2f} rad/s", round(diff, 3), passed, msg))
            if not passed:
                reasons.append(f"Steady-state speed {actual:.2f} rad/s exceeded absolute tolerance ±{tol:.2f} from target {target:.2f}")

        # 2. Steady-state speed percentage tolerance
        if "speed_tolerance_pct" in ac and "steady_state_speed" in expected:
            target = float(expected["steady_state_speed"])
            tol_pct = float(ac["speed_tolerance_pct"])
            actual = float(metrics.get("steady_state_speed", float("nan")))
            diff_pct = (abs(actual - target) / target * 100.0) if target != 0 else 0.0
            passed = diff_pct <= tol_pct
            msg = f"{diff_pct:.2f}% deviation (limit <= {tol_pct:.2f}%)"
            checks.append(CriterionCheck("speed_tolerance_pct", f"pct_dev <= {tol_pct:.2f}%", round(diff_pct, 3), passed, msg))
            if not passed:
                reasons.append(f"Steady-state speed error {diff_pct:.2f}% exceeded allowable percentage {tol_pct:.2f}%")

        # 3. Maximum Overshoot
        if "max_overshoot_pct" in ac:
            limit = float(ac["max_overshoot_pct"])
            actual = float(metrics.get("overshoot_pct", 0.0))
            passed = actual <= limit
            msg = f"Overshoot {actual:.2f}% (limit <= {limit:.2f}%)"
            checks.append(CriterionCheck("max_overshoot_pct", f"overshoot <= {limit:.2f}%", round(actual, 3), passed, msg))
            if not passed:
                reasons.append(f"Peak overshoot {actual:.2f}% exceeded maximum allowable limit {limit:.2f}%")

        # 4. Maximum Settling Time
        if "max_settling_time_s" in ac:
            limit = float(ac["max_settling_time_s"])
            actual = float(metrics.get("settling_time_s", float("inf")))
            passed = actual <= limit
            msg = f"Settling time {actual:.3f} s (limit <= {limit:.3f} s)"
            checks.append(CriterionCheck("max_settling_time_s", f"settling <= {limit:.3f} s", round(actual, 3), passed, msg))
            if not passed:
                reasons.append(f"Settling time {actual:.3f} s exceeded maximum allowable time {limit:.3f} s")

        # 5. Maximum Steady-State Error
        if "max_steady_state_error" in ac:
            limit = float(ac["max_steady_state_error"])
            actual = float(metrics.get("steady_state_error", float("inf")))
            passed = actual <= limit
            msg = f"Steady-state error {actual:.3f} rad/s (limit <= {limit:.3f} rad/s)"
            checks.append(CriterionCheck("max_steady_state_error", f"error <= {limit:.3f} rad/s", round(actual, 3), passed, msg))
            if not passed:
                reasons.append(f"Steady-state tracking error {actual:.3f} rad/s exceeded limit {limit:.3f} rad/s")

        # 6. Peak Armature Current
        if "max_peak_current_a" in ac:
            limit = float(ac["max_peak_current_a"])
            actual = float(metrics.get("peak_current_a", 0.0))
            passed = actual <= limit
            msg = f"Peak current {actual:.2f} A (limit <= {limit:.2f} A)"
            checks.append(CriterionCheck("max_peak_current_a", f"current <= {limit:.2f} A", round(actual, 3), passed, msg))
            if not passed:
                reasons.append(f"Peak transient current {actual:.2f} A exceeded electrical safety threshold {limit:.2f} A")

        # Overall Status Determination
        all_passed = all(c.passed for c in checks) and len(reasons) == 0
        final_status = "PASS" if all_passed else "FAIL"

        return TestOutcome(
            test_id=test_case.id,
            name=test_case.name,
            category=test_case.category,
            severity=test_case.severity,
            status=final_status,
            execution_time_ms=exec_time_ms,
            actual_metrics=metrics,
            expected_values=expected,
            acceptance_criteria=ac,
            criterion_checks=checks,
            failure_reasons=reasons,
            source=sim_result.source,
        )
