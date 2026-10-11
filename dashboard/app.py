"""
SimuVerify Interactive Streamlit Dashboard
==========================================
Interactive web application for exploring validation results, inspecting failure
diagnostics, filtering test scenarios, and plotting dynamic response curves.

Launch:
  streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Setup Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
REPORTS_DIR = PROJECT_ROOT / "reports"

from simuverify.config_loader import load_test_suite
from simuverify.reporting.plotter import plot_test_response
from simuverify.runner import TestRunner


def set_page_config():
    st.set_page_config(
        page_title="SimuVerify | Validation Dashboard",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def load_cached_results() -> dict | None:
    json_path = REPORTS_DIR / "validation_results.json"
    if json_path.is_file():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def run_tests_live(config_file: Path) -> dict:
    suite = load_test_suite(config_file)
    runner = TestRunner()
    result = runner.run_suite(suite)
    data = result.to_dict()
    # Save cache
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "validation_results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data, result.sim_traces


def main():
    set_page_config()

    st.title("⚡ SimuVerify — Dynamic System Validation Dashboard")
    st.caption("Automated requirements-based test execution, tolerance evaluation, and failure diagnostics.")

    # Sidebar Controls
    st.sidebar.header("🔧 Execution Controls")
    config_files = list(CONFIG_DIR.glob("*.json")) + list(CONFIG_DIR.glob("*.yaml"))
    config_names = [f.name for f in config_files]
    selected_config_name = st.sidebar.selectbox("Test Configuration", config_names, index=0 if config_names else None)

    col_btn1, col_btn2 = st.sidebar.columns(2)
    run_live = col_btn1.button("▶ Run Suite", type="primary", use_container_width=True)
    reload_cached = col_btn2.button("🔄 Reload", use_container_width=True)

    # State management
    if "results" not in st.session_state or run_live:
        if run_live and selected_config_name:
            cfg_path = CONFIG_DIR / selected_config_name
            with st.spinner("Executing dynamic simulations & validating criteria..."):
                results_data, traces = run_tests_live(cfg_path)
                st.session_state["results"] = results_data
                st.session_state["traces"] = traces
        else:
            cached = load_cached_results()
            if cached:
                st.session_state["results"] = cached
                st.session_state["traces"] = {}
            elif selected_config_name:
                cfg_path = CONFIG_DIR / selected_config_name
                results_data, traces = run_tests_live(cfg_path)
                st.session_state["results"] = results_data
                st.session_state["traces"] = traces

    results = st.session_state.get("results")
    if not results:
        st.warning("No validation results available. Click 'Run Suite' to execute tests.")
        return

    # Environment Banner
    source_label = results.get("outcomes", [{}])[0].get("source", "CI Mode")
    if "CI Mode" in source_label:
        st.info(
            "ℹ️ **Environment:** Executed via **SimuVerify Deterministic Python Engine (Demonstration & CI Validation Mode)**. "
            "To execute in native MathWorks MATLAB/Simulink, run `python scripts/run_simuverify.py --mode matlab` or `matlab/runner/run_all_tests.m`."
        )
    else:
        st.success(f"✅ **Environment:** Executed via **{source_label}**.")

    # Top KPI Metrics
    total = results.get("total_tests", 0)
    passed = results.get("passed_tests", 0)
    failed = results.get("failed_tests", 0)
    errors = results.get("error_tests", 0)
    pass_rate = results.get("pass_percentage", 0.0)
    duration = results.get("total_duration_ms", 0.0)

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Total Scenarios", total)
    kpi2.metric("Passed (Within Limits)", passed, delta=f"{pass_rate:.1f}%")
    kpi3.metric("Failed (Tolerance Breaches)", failed, delta_color="inverse")
    kpi4.metric("Errors (Invalid/Schema)", errors, delta_color="inverse")
    kpi5.metric("Execution Duration", f"{duration:.1f} ms")

    # Progress bar
    st.progress(pass_rate / 100.0)

    # Sidebar Filters
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filter Scenarios")
    all_statuses = ["ALL", "PASS", "FAIL", "ERROR"]
    status_filter = st.sidebar.selectbox("Filter by Status", all_statuses, index=0)

    all_categories = ["ALL", "nominal", "boundary", "fault_abnormal", "invalid_config"]
    category_filter = st.sidebar.selectbox("Filter by Category", all_categories, index=0)

    all_severities = ["ALL", "CRITICAL", "MAJOR", "MINOR"]
    severity_filter = st.sidebar.selectbox("Filter by Severity", all_severities, index=0)

    # Filter outcomes
    raw_outcomes = results.get("outcomes", [])
    filtered_outcomes = []
    for o in raw_outcomes:
        if status_filter != "ALL" and o.get("status") != status_filter:
            continue
        if category_filter != "ALL" and o.get("category") != category_filter:
            continue
        if severity_filter != "ALL" and o.get("severity") != severity_filter:
            continue
        filtered_outcomes.append(o)

    # Main Tab Layout
    tab_overview, tab_details, tab_raw = st.tabs(["📊 Summary Table", "🔬 Deep Diagnostic Inspection", "📄 JSON Metadata"])

    with tab_overview:
        st.subheader(f"Test Execution Results ({len(filtered_outcomes)} of {total} shown)")

        # Prepare summary dataframe
        table_rows = []
        for o in filtered_outcomes:
            metrics = o.get("actual_metrics", {})
            expected = o.get("expected_values", {})
            table_rows.append({
                "Test ID": o.get("test_id"),
                "Scenario Name": o.get("name"),
                "Status": o.get("status"),
                "Category": o.get("category"),
                "Severity": o.get("severity"),
                "Speed (Actual)": f"{metrics.get('steady_state_speed', 0.0):.2f}" if metrics else "N/A",
                "Speed (Target)": f"{expected.get('steady_state_speed', 0.0):.2f}" if expected else "N/A",
                "Overshoot": f"{metrics.get('overshoot_pct', 0.0):.1f}%" if metrics else "N/A",
                "Settling Time": f"{metrics.get('settling_time_s', 0.0):.3f}s" if metrics else "N/A",
                "Peak Current": f"{metrics.get('peak_current_a', 0.0):.1f}A" if metrics else "N/A",
                "Duration (ms)": f"{o.get('execution_time_ms', 0.0):.1f}",
            })

        if table_rows:
            df = pd.DataFrame(table_rows)

            def highlight_status(val):
                if val == "PASS":
                    return "background-color: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: bold;"
                elif val == "FAIL":
                    return "background-color: rgba(239, 68, 68, 0.2); color: #ef4444; font-weight: bold;"
                elif val == "ERROR":
                    return "background-color: rgba(245, 158, 11, 0.2); color: #f59e0b; font-weight: bold;"
                return ""

            styled_df = df.style.map(highlight_status, subset=["Status"])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("No test cases match the active filter criteria.")

    with tab_details:
        st.subheader("Detailed Test Case Inspection & Simulation Traces")
        if filtered_outcomes:
            case_options = [f"{o.get('test_id')} - {o.get('name')} [{o.get('status')}]" for o in filtered_outcomes]
            selected_case_idx = st.selectbox("Select Scenario to Inspect", range(len(case_options)), format_func=lambda x: case_options[x])
            selected_outcome = filtered_outcomes[selected_case_idx]

            # Header info
            c_id = selected_outcome.get("test_id")
            c_status = selected_outcome.get("status")
            c_name = selected_outcome.get("name")
            c_cat = selected_outcome.get("category")
            c_sev = selected_outcome.get("severity")

            st.markdown(f"### `{c_id}`: {c_name}")
            col_b1, col_b2, col_b3 = st.columns(3)
            col_b1.markdown(f"**Status:** `{c_status}`")
            col_b2.markdown(f"**Category:** `{c_cat}`")
            col_b3.markdown(f"**Severity:** `{c_sev}`")

            # Failure diagnosis callout
            reasons = selected_outcome.get("failure_reasons", [])
            if reasons:
                st.error("⚠️ **Validation Failure Diagnosis:**\n- " + "\n- ".join(reasons))

            # Criteria Checks
            st.markdown("#### Acceptance Criteria Checks")
            checks = selected_outcome.get("criterion_checks", [])
            if checks:
                check_df = pd.DataFrame(checks)
                check_df["Result"] = check_df["passed"].apply(lambda p: "✅ PASS" if p else "❌ FAIL")
                st.dataframe(check_df[["criterion", "rule", "actual", "Result", "message"]], use_container_width=True, hide_index=True)
            else:
                st.info("No criterion checks evaluated (e.g. invalid configuration or missing output).")

            # Plot response
            st.markdown("#### Time-Domain Simulation Response")
            plot_path = REPORTS_DIR / "plots" / f"{c_id}_response.png"
            if plot_path.is_file():
                st.image(str(plot_path), caption=f"Response curve for {c_id}", use_container_width=True)
            else:
                st.info("Response curve plot image not found. Run CLI with plot generation enabled.")
        else:
            st.info("No test cases match active filters.")

    with tab_raw:
        st.subheader("Raw Suite Execution JSON")
        st.json(results)


if __name__ == "__main__":
    main()
