"""
Configuration Loader and Schema Validator
==========================================
Loads test definitions from JSON or YAML configuration files and verifies
that mandatory attributes, data types, and numerical ranges conform to specifications.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None


REQUIRED_TEST_KEYS = {
    "id",
    "name",
    "category",
    "severity",
    "inputs",
    "expected",
    "acceptance_criteria",
}

REQUIRED_INPUT_KEYS = {
    "target_speed",
    "sim_time",
}

ALLOWED_CATEGORIES = {"nominal", "boundary", "fault_abnormal", "invalid_config"}
ALLOWED_SEVERITIES = {"CRITICAL", "MAJOR", "MINOR"}


@dataclass
class ValidationIssue:
    field: str
    message: str
    is_fatal: bool = True


@dataclass
class TestCaseConfig:
    __test__ = False
    id: str
    name: str
    category: str
    severity: str
    description: str
    inputs: Dict[str, Any]
    expected: Dict[str, Any]
    acceptance_criteria: Dict[str, Any]
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.is_fatal for issue in self.issues)


@dataclass
class TestSuiteConfig:
    __test__ = False
    suite_name: str
    version: str
    description: str
    system_under_test: Dict[str, Any]
    test_cases: List[TestCaseConfig]
    source_file: str


def validate_test_case_schema(case_data: Dict[str, Any]) -> List[ValidationIssue]:
    """Inspects a single raw test case dictionary and returns identified issues."""
    issues: List[ValidationIssue] = []

    # Check required top-level keys
    missing_keys = REQUIRED_TEST_KEYS - set(case_data.keys())
    for key in missing_keys:
        issues.append(ValidationIssue(field=key, message=f"Missing mandatory field '{key}'"))

    if missing_keys:
        return issues

    # Validate category and severity
    category = str(case_data.get("category", "")).lower()
    if category not in ALLOWED_CATEGORIES:
        issues.append(
            ValidationIssue(
                field="category",
                message=f"Category '{category}' must be one of {sorted(ALLOWED_CATEGORIES)}",
                is_fatal=False,
            )
        )

    severity = str(case_data.get("severity", "")).upper()
    if severity not in ALLOWED_SEVERITIES:
        issues.append(
            ValidationIssue(
                field="severity",
                message=f"Severity '{severity}' must be one of {sorted(ALLOWED_SEVERITIES)}",
                is_fatal=False,
            )
        )

    # Validate inputs
    inputs = case_data.get("inputs", {})
    if not isinstance(inputs, dict):
        issues.append(ValidationIssue(field="inputs", message="'inputs' must be a dictionary"))
    else:
        for req_in in REQUIRED_INPUT_KEYS:
            if req_in not in inputs:
                issues.append(
                    ValidationIssue(
                        field=f"inputs.{req_in}",
                        message=f"Missing mandatory input parameter '{req_in}'",
                    )
                )

        if "sim_time" in inputs:
            try:
                sim_time = float(inputs["sim_time"])
                if sim_time <= 0:
                    issues.append(
                        ValidationIssue(
                            field="inputs.sim_time",
                            message=f"Simulation time must be positive (got {sim_time})",
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        field="inputs.sim_time",
                        message=f"Simulation time must be numeric (got {inputs['sim_time']})",
                    )
                )

        if "sample_time" in inputs:
            try:
                dt = float(inputs["sample_time"])
                if dt <= 0:
                    issues.append(
                        ValidationIssue(
                            field="inputs.sample_time",
                            message=f"Sample time step must be strictly positive (got {dt})",
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        field="inputs.sample_time",
                        message=f"Sample time must be numeric (got {inputs['sample_time']})",
                    )
                )

    # Validate acceptance_criteria
    ac = case_data.get("acceptance_criteria", {})
    if not isinstance(ac, dict):
        issues.append(
            ValidationIssue(
                field="acceptance_criteria",
                message="'acceptance_criteria' must be a dictionary",
            )
        )

    return issues


def load_test_suite(file_path: str | Path) -> TestSuiteConfig:
    """
    Parses a test suite file from JSON or YAML and constructs a validated TestSuiteConfig.
    Raises FileNotFoundError or ValueError on unrecoverable syntax errors.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Test suite configuration not found: {path.resolve()}")

    content_str = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise ImportError("PyYAML is required to load YAML test suites. Run 'pip install PyYAML' or use JSON format.")
        data = yaml.safe_load(content_str)
    else:
        data = json.loads(content_str)

    if not isinstance(data, dict):
        raise ValueError("Root configuration element must be a dictionary")

    suite_name = data.get("suite_name", "Untitled Test Suite")
    version = data.get("version", "1.0.0")
    description = data.get("description", "")
    system_under_test = data.get("system_under_test", {})

    raw_cases = data.get("test_cases", [])
    if not isinstance(raw_cases, list):
        raise ValueError("'test_cases' field must be a list")

    parsed_cases: List[TestCaseConfig] = []
    for raw in raw_cases:
        issues = validate_test_case_schema(raw)
        case_id = raw.get("id", "UNKNOWN-ID")
        name = raw.get("name", "Unnamed Test Case")
        category = raw.get("category", "nominal")
        severity = raw.get("severity", "MAJOR")
        desc = raw.get("description", "")
        inputs = raw.get("inputs", {})
        expected = raw.get("expected", {})
        ac = raw.get("acceptance_criteria", {})

        parsed_cases.append(
            TestCaseConfig(
                id=case_id,
                name=name,
                category=category,
                severity=severity,
                description=desc,
                inputs=inputs,
                expected=expected,
                acceptance_criteria=ac,
                issues=issues,
            )
        )

    return TestSuiteConfig(
        suite_name=suite_name,
        version=version,
        description=description,
        system_under_test=system_under_test,
        test_cases=parsed_cases,
        source_file=str(path.resolve()),
    )
