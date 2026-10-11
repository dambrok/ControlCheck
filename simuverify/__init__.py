"""
SimuVerify: MATLAB/Simulink Automated Testing & Validation Framework
=====================================================================
A modular, requirements-based test execution and verification framework designed
for engineering validation of dynamic systems and control models.

Architectural principles:
  1. Separation of Concerns: Test specification, model execution, result validation,
     and reporting are decoupled into independent modules.
  2. Dual-Mode Execution: Supports native MATLAB/Simulink batch execution when licensed,
     with a deterministic standalone Python simulation engine for standard CI/CD runners.
  3. Strict Verification: Non-zero-trust evaluation against explicit numerical tolerances
     and envelope constraints without fabricating results.
"""

__version__ = "1.0.0"
__author__ = "SimuVerify Contributors"

from simuverify.config_loader import load_test_suite, validate_test_case_schema
from simuverify.engine.simulator import DCMotorSimulator, SimulationResult
from simuverify.engine.validator import ResultValidator, TestOutcome
from simuverify.runner import TestRunner, SuiteExecutionResult

__all__ = [
    "__version__",
    "load_test_suite",
    "validate_test_case_schema",
    "DCMotorSimulator",
    "SimulationResult",
    "ResultValidator",
    "TestOutcome",
    "TestRunner",
    "SuiteExecutionResult",
]
