"""
Unit Tests for Configuration Loader and Schema Validator
"""

import json
from pathlib import Path
import pytest
from simuverify.config_loader import (
    TestCaseConfig,
    load_test_suite,
    validate_test_case_schema,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_load_valid_json_suite():
    json_path = PROJECT_ROOT / "config" / "test_cases.json"
    suite = load_test_suite(json_path)

    assert suite.suite_name is not None
    assert len(suite.test_cases) >= 5
    assert any(c.id == "TC-NOM-01" for c in suite.test_cases)
    assert any(c.id == "TC-FLT-01" for c in suite.test_cases)


def test_load_valid_yaml_suite():
    yaml_path = PROJECT_ROOT / "config" / "test_cases.yaml"
    suite = load_test_suite(yaml_path)

    assert suite.suite_name is not None
    assert len(suite.test_cases) >= 5
    assert any(c.id == "TC-NOM-01" for c in suite.test_cases)


def test_missing_file_raises_not_found():
    with pytest.raises(FileNotFoundError):
        load_test_suite(PROJECT_ROOT / "config" / "non_existent_suite.json")


def test_validate_test_case_schema_missing_required():
    incomplete_case = {
        "id": "TC-BAD-01",
        "name": "Bad Case",
        # missing category, severity, inputs, expected, acceptance_criteria
    }
    issues = validate_test_case_schema(incomplete_case)
    missing_fields = {iss.field for iss in issues if iss.is_fatal}
    assert "inputs" in missing_fields
    assert "expected" in missing_fields
    assert "acceptance_criteria" in missing_fields


def test_validate_negative_sim_time():
    invalid_time_case = {
        "id": "TC-BAD-02",
        "name": "Bad Sim Time",
        "category": "nominal",
        "severity": "MINOR",
        "inputs": {"target_speed": 100.0, "sim_time": -5.0},
        "expected": {"steady_state_speed": 100.0},
        "acceptance_criteria": {"speed_tolerance_abs": 2.0},
    }
    issues = validate_test_case_schema(invalid_time_case)
    assert any("sim_time" in iss.field and iss.is_fatal for iss in issues)


def test_validate_valid_case():
    good_case = {
        "id": "TC-GOOD-01",
        "name": "Proper Case",
        "category": "nominal",
        "severity": "MAJOR",
        "inputs": {"target_speed": 50.0, "sim_time": 2.0, "sample_time": 0.001},
        "expected": {"steady_state_speed": 50.0},
        "acceptance_criteria": {"speed_tolerance_abs": 1.0},
    }
    issues = validate_test_case_schema(good_case)
    assert not any(iss.is_fatal for iss in issues)
