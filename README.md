# SimuVerify: MATLAB/Simulink Automated Testing & Validation Framework

[![CI Pipeline](https://img.shields.io/badge/CI-Passing-success?style=flat-square&logo=github-actions)](https://github.com/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?style=flat-square&logo=python)](https://www.python.org/)
[![MATLAB](https://img.shields.io/badge/MATLAB-R2020b+-orange?style=flat-square&logo=mathworks)](https://www.mathworks.com/products/matlab.html)
[![Simulink Compatible](https://img.shields.io/badge/Simulink-Continuous%20Verification-red?style=flat-square&logo=mathworks)](https://www.mathworks.com/products/simulink.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**SimuVerify** is a modular, requirements-based automated test execution and validation framework designed for dynamic systems and control models. It bridges Model-Based Design (MBD) principles with modern Continuous Integration (CI/CD) pipelines, enabling rigorous verification of electromechanical models against formal acceptance tolerances.

Inspired by industry functional safety standards (ISO 26262 / DO-178C) and Model-in-the-Loop (MIL) verification patterns, SimuVerify decouples test definition, dynamic simulation, acceptance validation, and multi-channel reporting.

---

## 🌟 Key Features

- **Declarative Test Case Management**: Store test scenarios in human-readable JSON (`config/test_cases.json`) or YAML (`config/test_cases.yaml`) with structured metadata, inputs, expected outcomes, numerical tolerances, and severity levels (`CRITICAL`, `MAJOR`, `MINOR`).
- **Comprehensive Scenario Coverage**: Out-of-the-box test suites covering nominal step responses, load disturbance rejection, actuator voltage saturation, heavy inertial payloads, intentional stall overloads (`TC-FLT-01`), high-gain ringing (`TC-FLT-02`), and configuration error traps (`TC-ERR-01`, `TC-ERR-02`).
- **Dual-Mode Architectural Engine**:
  - **Standalone CI Mode**: Powered by a 100% deterministic Runge-Kutta 4th-order (RK4) Python simulation engine. Runs out-of-the-box on standard GitHub-hosted runners without proprietary licenses.
  - **Native MATLAB/Simulink Mode**: Modular MATLAB runner (`matlab/runner/run_all_tests.m`) and programmatic Simulink model generator (`matlab/sim/build_simulink_model.m`). Transparently utilizes `sim()` when Simulink is licensed.
- **Strict, Non-Zero-Trust Verification**: Evaluates multi-point acceptance criteria—absolute tolerance, percentage deviation, peak percentage overshoot ($M_p$), settling time ($t_s$), steady-state error ($e_{ss}$), and electrical current safety thresholds ($I_{\text{peak}}$).
- **Publication-Ready Automated Reports**:
  - **Interactive HTML Report**: Self-contained report with KPI cards, pass/fail progress distribution, instant status filtering, diagnostic drawers, and embedded time-domain response curves.
  - **Tabular CSV Summary**: Formatted for spreadsheet inspection and automated test database ingestion.
  - **Structured JSON Dataset**: Full machine-readable test execution telemetry.
- **Interactive Streamlit Dashboard**: Optional GUI dashboard (`dashboard/app.py`) for filtering scenarios, analyzing failure diagnostics, and exploring simulation response curves.
- **Continuous Integration Ready**: Pre-configured GitHub Actions workflow (`.github/workflows/ci.yml`) testing on Ubuntu and Windows.

---

## 🏗️ Architecture & Execution Flow

SimuVerify strictly separates test specification, model execution, result validation, and reporting:

```
                          +-------------------------+
                          |   config/test_cases.json|
                          |   config/test_cases.yaml|
                          +------------+------------+
                                       |
                                       v
                          +-------------------------+
                          |      TestRunner         |
                          +------------+------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
                   v                                       v
     [Mode: CI / Headless]                   [Mode: Local MATLAB]
+------------------------------+       +------------------------------+
|  DCMotorSimulator (Python)   |       |   MATLAB / Simulink Engine   |
|  - 4th-Order RK4 Integrator  |       |   - run_simulink_model.m     |
|  - Drive Current Limiter     |       |   - dc_motor_model.m (ODE)   |
|  - Anti-Windup PID Control   |       |   - sim('dc_motor_control')  |
+--------------+---------------+       +--------------+---------------+
               |                                      |
               +-------------------+------------------+
                                   |
                                   v
                      +--------------------------+
                      |     ResultValidator      |
                      |  - Speed Tolerance (Abs/%)|
                      |  - Overshoot Limit (%)   |
                      |  - Settling Time (s)     |
                      |  - Current Limit (A)     |
                      +------------+-------------+
                                   |
                                   v
             +---------------------+---------------------+
             |                     |                     |
             v                     v                     v
    +-----------------+   +-----------------+   +-----------------+
    |  HTML Report    |   |   CSV Summary   |   |   JSON Data     |
    | (Interactive UI)|   |  (Spreadsheet)  |   |   (Telemetry)   |
    +-----------------+   +-----------------+   +-----------------+
```

---

## 📁 Repository Structure

```
MATLAB-Simulink-Automated-Testing/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Multi-OS GitHub Actions CI workflow
├── config/
│   ├── test_cases.json                # Primary test suite specification
│   └── test_cases.yaml                # YAML test suite specification
├── dashboard/
│   └── app.py                         # Interactive Streamlit validation dashboard
├── docs/
│   ├── ARCHITECTURE.md                # Detailed architecture & sequence diagrams
│   └── LEARNING_GUIDE.md             # ECE student guide & interview preparation
├── matlab/
│   ├── config/
│   │   └── load_test_cases.m          # MATLAB JSON configuration parser
│   ├── reporting/
│   │   ├── export_csv.m               # MATLAB CSV report generator
│   │   └── export_html.m              # MATLAB HTML report generator
│   ├── runner/
│   │   ├── ModelExecutor.m            # Decoupled model execution class
│   │   ├── ResultValidator.m          # Numerical acceptance validation class
│   │   ├── TestRunner.m               # Test suite runner orchestrator
│   │   └── run_all_tests.m            # Top-level MATLAB test entry point
│   └── sim/
│       ├── build_simulink_model.m     # Programmatic Simulink model builder (.slx)
│       ├── dc_motor_model.m           # Pure MATLAB RK4 ODE simulation solver
│       └── run_simulink_model.m       # Simulink harness with ODE fallback
├── models/
│   ├── model_metadata.json            # DC motor electromechanical specifications
│   └── README.md                      # System Under Test equations & block docs
├── reports/                           # Output artifacts directory
│   ├── plots/                         # Standalone time-domain response PNGs
│   ├── validation_report.html         # Interactive HTML report
│   ├── validation_results.json        # Machine-readable JSON results
│   └── validation_summary.csv         # Tabular CSV summary
├── scripts/
│   ├── launch_dashboard.bat           # One-click Windows dashboard launcher
│   └── run_simuverify.py              # CLI test suite orchestrator
├── simuverify/                        # Core Python framework package
│   ├── config_loader.py               # Config loader & schema validator
│   ├── engine/
│   │   ├── simulator.py               # Deterministic DC motor dynamic simulation
│   │   └── validator.py               # Numeric criterion checking & failure analysis
│   ├── reporting/
│   │   ├── exporter_csv.py            # CSV report export
│   │   ├── exporter_html.py           # Self-contained HTML report export
│   │   └── plotter.py                 # Time-domain response curve generator
│   └── runner.py                      # Python test runner orchestrator
├── tests/                             # Automated pytest suite (19 unit/integration tests)
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_reporting.py
│   ├── test_simulator.py
│   └── test_validator.py
├── .gitignore
├── LICENSE                            # MIT License with dependency considerations
├── README.md
└── requirements.txt                   # Pinned Python dependencies
```

---

## ⚡ Quickstart & Setup Instructions

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.11, 3.12, 3.13)
- Optional: MathWorks MATLAB R2020b+ (with Simulink)

### 2. Installation
Clone or navigate to the project directory and install Python dependencies:
```bash
pip install -r requirements.txt
```

---

## 🚀 Exact Commands to Run the Project Locally

### 1. Run Automated Framework Unit Tests
Verify all 19 unit and integration tests for the configuration parser, ODE solver, validation engine, report exporter, and CLI:
```bash
pytest tests/ -v
```

### 2. Run the Verification Suite (CLI)
Execute the complete validation suite, check acceptance tolerances, and generate all report formats (`reports/validation_report.html`, `reports/validation_summary.csv`, `reports/validation_results.json`, and response plots):
```bash
python scripts/run_simuverify.py --config config/test_cases.json --output-dir reports/ --format all
```

**Verbose Console Mode (shows measured telemetry per test):**
```bash
python scripts/run_simuverify.py --verbose
```

### 3. Launch the Interactive Dashboard
Explore results, inspect failure diagnostics, and view interactive simulation curves in your browser:
```bash
streamlit run dashboard/app.py
```
*(On Windows, you can also double-click `scripts/launch_dashboard.bat`)*

---

## 🔬 Running in MATLAB / Simulink

When MATLAB is installed on your workstation, you can run the native MATLAB test harness directly:

### 1. Pure MATLAB Test Execution (No Toolboxes Required)
Launch MATLAB, navigate to this project folder, and run:
```matlab
addpath(genpath('matlab'));
summary = run_all_tests;
```
This executes all 9 test scenarios using the native MATLAB ODE solver (`dc_motor_model.m`), evaluates acceptance criteria, prints console progress, and exports `reports/validation_report.html` and `reports/validation_summary.csv`.

### 2. Generate and Run the Simulink Model (`.slx`)
If you have Simulink installed and want to visually inspect or simulate the block diagram:
```matlab
addpath(genpath('matlab'));

% Programmatically create models/dc_motor_control.slx
build_simulink_model;

% Open and view the block diagram in Simulink
open_system('models/dc_motor_control.slx');

% Run the test harness using the Simulink model
summary = run_all_tests;
```

---

## 📊 Sample Validation Results

When executing `config/test_cases.json`, SimuVerify evaluates 9 scenarios:

| Test ID | Scenario Name | Category | Severity | Status | Measured Speed | Overshoot | Settling | Current | Diagnostic Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TC-NOM-01` | Nominal Step Response | Nominal | CRITICAL | **`PASS`** | 100.0 rad/s | 0.0% | 0.50 s | 12.0 A | Within standard tolerance limits |
| `TC-NOM-02` | Load Disturbance Rejection | Nominal | MAJOR | **`PASS`** | 80.0 rad/s | 0.0% | 0.42 s | 12.0 A | Integral controller rejects 0.5 N*m load |
| `TC-NOM-03` | Low-Speed Regulation | Nominal | MINOR | **`PASS`** | 25.0 rad/s | 0.0% | 0.28 s | 12.0 A | Smooth tracking at low setpoint |
| `TC-BND-01` | High-Speed Saturation | Boundary | MAJOR | **`PASS`** | 192.0 rad/s | 0.0% | 1.82 s | 12.0 A | Operates safely near 24V supply cap |
| `TC-BND-02` | High Rotor Inertia | Boundary | MAJOR | **`PASS`** | 100.0 rad/s | 0.0% | 1.95 s | 12.0 A | Stays stable under 5x mechanical inertia |
| `TC-FLT-01` | Severe Overload Stall | Fault | CRITICAL | **`FAIL`** | 0.0 rad/s | 0.0% | 4.00 s | 12.0 A | **Intentional Failure:** Motor stalls under 4.5 N*m; steady-state speed breached |
| `TC-FLT-02` | High Gain Overshoot | Fault | MAJOR | **`FAIL`** | 100.0 rad/s | 34.2% | 1.65 s | 12.0 A | **Intentional Failure:** Detuned Kp=35 causes 34.2% overshoot (limit 12.0%) |
| `TC-ERR-01` | Invalid Sim Duration | Invalid | MINOR | **`ERROR`** | N/A | N/A | N/A | N/A | **Config Error:** Negative simulation time caught by schema validator |
| `TC-ERR-02` | Missing Input Key | Invalid | MINOR | **`ERROR`** | N/A | N/A | N/A | N/A | **Schema Trap:** Missing mandatory `target_speed` field caught |

> **Summary:** 5 Passed (55.6%), 2 Failed (Intentional verification traps), 2 Errors (Configuration guards).

---

## 🛡️ Integrity Guarantee

- **No Fabricated Results**: When running in standalone CI mode, reports are explicitly stamped with:  
  `DEMONSTRATION & CI VALIDATION MODE (SimuVerify Deterministic Python Engine)`.
- When executed in MATLAB with Simulink, the banner dynamically reflects:  
  `NATIVE MATLAB / SIMULINK EXECUTION`.
- SimuVerify never asserts that a Simulink simulation passed unless `sim()` was genuinely executed.

---

## 🔮 Limitations & Future Roadmap

1. **Current Limitations**:
   - The default demonstration model focuses on single-input, single-output (SISO) speed control.
   - Fixed-step ODE integration is utilized; variable-step stiff solvers (e.g. `ode15s`) are not yet integrated into the Python fallback engine.
2. **Future Enhancements**:
   - **Signal Envelope Tolerancing**: Support upper and lower time-varying bound envelopes (tolerancing masks) in addition to scalar metrics.
   - **Automated C Code Generation (SIL)**: Compile generated C code using GCC and execute SIL verification.
   - **CAN Bus Telemetry Mocking**: Support virtual CAN / socketCAN injection for automotive Hardware-in-the-Loop test benches.

---

## 📜 License & Acknowledgments

This project is open-source under the [MIT License](LICENSE).  
- **Original Implementation**: All code, models, tests, configurations, and documentation were independently designed and implemented.
- **Trademark Notice**: MATLAB and Simulink are registered trademarks of The MathWorks, Inc. This project is not affiliated with or endorsed by MathWorks.
