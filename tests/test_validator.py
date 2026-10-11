"""
Unit Tests for Result Validator and Failure Categorization
"""

import pytest
import numpy as np
from simuverify.config_loader import TestCaseConfig, ValidationIssue
from simuverify.engine.simulator import SimulationResult
from simuverify.engine.validator import ResultValidator


@pytest.fixture
def validator():
    return ResultValidator()


def create_dummy_case(
    case_id="TC-01",
    target_speed=100.0,
    speed_tol=2.0,
    max_overshoot=10.0,
    issues=None,
):
    return TestCaseConfig(
        id=case_id,
        name="Dummy Test",
        category="nominal",
        severity="MAJOR",
        description="Test description",
        inputs={"target_speed": target_speed, "sim_time": 2.0},
        expected={"steady_state_speed": target_speed},
        acceptance_criteria={
            "speed_tolerance_abs": speed_tol,
            "max_overshoot_pct": max_overshoot,
        },
        issues=issues or [],
    )


def test_validator_passes_when_within_tolerances(validator):
    case = create_dummy_case(target_speed=100.0, speed_tol=2.0, max_overshoot=10.0)
    sim_result = SimulationResult(
        time=np.array([0.0, 1.0, 2.0]),
        speed=np.array([0.0, 99.5, 100.2]),
        current=np.array([0.0, 2.0, 0.5]),
        voltage=np.array([0.0, 10.0, 10.0]),
        target_speed=100.0,
        metrics={
            "steady_state_speed": 100.2,
            "steady_state_error": 0.2,
            "overshoot_pct": 2.0,
            "settling_time_s": 0.8,
            "peak_current_a": 5.0,
        },
        raw_inputs={},
    )
    outcome = validator.evaluate(case, sim_result)

    assert outcome.status == "PASS"
    assert outcome.passed is True
    assert len(outcome.failure_reasons) == 0


def test_validator_fails_when_overshoot_exceeded(validator):
    case = create_dummy_case(target_speed=100.0, speed_tol=2.0, max_overshoot=10.0)
    sim_result = SimulationResult(
        time=np.array([0.0, 1.0, 2.0]),
        speed=np.array([0.0, 135.0, 100.0]),
        current=np.array([0.0, 5.0, 0.5]),
        voltage=np.array([0.0, 15.0, 10.0]),
        target_speed=100.0,
        metrics={
            "steady_state_speed": 100.0,
            "steady_state_error": 0.0,
            "overshoot_pct": 35.0,  # Breaches max 10.0%
            "settling_time_s": 1.2,
            "peak_current_a": 8.0,
        },
        raw_inputs={},
    )
    outcome = validator.evaluate(case, sim_result)

    assert outcome.status == "FAIL"
    assert outcome.passed is False
    assert any("Peak overshoot" in r for r in outcome.failure_reasons)


def test_validator_reports_error_on_invalid_case_config(validator):
    case = create_dummy_case(
        issues=[ValidationIssue(field="inputs.sim_time", message="Negative duration", is_fatal=True)]
    )
    outcome = validator.evaluate(case, None)

    assert outcome.status == "ERROR"
    assert any("Invalid Test Configuration" in r for r in outcome.failure_reasons)


def test_validator_reports_error_on_simulation_exception(validator):
    case = create_dummy_case()
    outcome = validator.evaluate(case, None, exec_error="ValueError: Singular Matrix")

    assert outcome.status == "ERROR"
    assert any("Execution Exception" in r for r in outcome.failure_reasons)
