"""
HTML Report Exporter
====================
Generates a self-contained, publication-ready, interactive HTML verification report
with embedded charts, filterable tables, and diagnostic detail drawers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Union
from simuverify.reporting.plotter import generate_all_plots
from simuverify.runner import SuiteExecutionResult


def export_to_html(
    result: SuiteExecutionResult,
    output_path: Union[str, Path],
    plots_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Generates an interactive, standalone HTML report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Generate plots if traces are available
    p_dir = Path(plots_dir) if plots_dir else path.parent / "plots"
    outcome_map = {o.test_id: o for o in result.outcomes}
    encoded_plots = generate_all_plots(result.sim_traces, outcome_map, p_dir)

    # Determine execution environment banner
    is_ci_mode = any("CI Mode" in o.source for o in result.outcomes) or len(result.outcomes) == 0

    if is_ci_mode:
        banner_badge = "DEMONSTRATION & CI VALIDATION MODE"
        banner_class = "banner-ci"
        banner_desc = (
            "Executed via the <strong>SimuVerify Deterministic Python Engine</strong>. "
            "All physical ODE dynamics and PID control loops were numerically solved using 4th-Order Runge-Kutta (RK4) integration. "
            "To execute with native MathWorks MATLAB/Simulink, run <code>matlab/runner/run_all_tests.m</code> or "
            "<code>python scripts/run_simuverify.py --mode matlab</code>."
        )
    else:
        banner_badge = "NATIVE MATLAB / SIMULINK EXECUTION"
        banner_class = "banner-matlab"
        banner_desc = (
            "Executed via <strong>MathWorks MATLAB / Simulink</strong>. "
            "Model states and signal logging traces were extracted directly from the Simulink simulation harness."
        )

    # Build rows HTML
    table_rows_html = []
    for o in result.outcomes:
        status_class = f"badge-{o.status.lower()}"
        sev_class = f"badge-sev-{o.severity.lower()}"
        cat_class = f"badge-cat-{o.category.replace('_', '-')}"

        metrics = o.actual_metrics
        expected = o.expected_values
        ac = o.acceptance_criteria

        speed_val = f"{metrics.get('steady_state_speed', 0.0):.2f}" if metrics else "N/A"
        speed_target = f"{expected.get('steady_state_speed', 0.0):.2f}" if expected else "N/A"
        overshoot_val = f"{metrics.get('overshoot_pct', 0.0):.2f}%" if metrics else "N/A"
        settling_val = f"{metrics.get('settling_time_s', 0.0):.3f}s" if metrics else "N/A"
        current_val = f"{metrics.get('peak_current_a', 0.0):.2f}A" if metrics else "N/A"

        # Diagnostic message or checks
        checks_html = []
        for c in o.criterion_checks:
            c_icon = "✓" if c.passed else "✗"
            c_class = "check-pass" if c.passed else "check-fail"
            checks_html.append(
                f"<div class='check-item {c_class}'>"
                f"<span class='check-icon'>{c_icon}</span>"
                f"<span class='check-name'>{c.criterion_name}:</span> "
                f"<span class='check-rule'>{c.expected_rule}</span> "
                f"<span class='check-msg'>({c.message})</span>"
                f"</div>"
            )

        checks_str = "".join(checks_html) if checks_html else "<em>No criterion checks performed.</em>"

        failure_box_html = ""
        if o.failure_reasons:
            reasons_li = "".join(f"<li>{r}</li>" for r in o.failure_reasons)
            failure_box_html = f"""
            <div class="failure-callout">
                <h4>⚠️ Validation Failure Diagnosis</h4>
                <ul>{reasons_li}</ul>
            </div>
            """

        plot_img_html = ""
        if o.test_id in encoded_plots:
            plot_img_html = f"""
            <div class="plot-container">
                <h4>Time-Domain Simulation Response</h4>
                <img src="data:image/png;base64,{encoded_plots[o.test_id]}" alt="Response Curve for {o.test_id}" class="plot-img" />
            </div>
            """

        row_html = f"""
        <tr class="test-row status-{o.status.lower()} sev-{o.severity.lower()} cat-{o.category.lower()}" onclick="toggleDetails('{o.test_id}')">
            <td class="font-mono font-bold">{o.test_id}</td>
            <td><strong>{o.name}</strong></td>
            <td><span class="badge {cat_class}">{o.category}</span></td>
            <td><span class="badge {sev_class}">{o.severity}</span></td>
            <td><span class="badge {status_class}">{o.status}</span></td>
            <td>{speed_val} / {speed_target} rad/s</td>
            <td>{overshoot_val}</td>
            <td>{settling_val}</td>
            <td>{current_val}</td>
            <td><button type="button" class="btn-toggle">Inspect ▼</button></td>
        </tr>
        <tr id="details-{o.test_id}" class="details-row" style="display: none;">
            <td colspan="10">
                <div class="details-card">
                    {failure_box_html}
                    <div class="grid-2col">
                        <div>
                            <h4>Test Acceptance Criteria Verification</h4>
                            <div class="checks-list">{checks_str}</div>
                            <h4 style="margin-top:16px;">Test Specification & Inputs</h4>
                            <div class="spec-box">
                                <p><strong>Execution Source:</strong> {o.source}</p>
                                <p><strong>Execution Time:</strong> {o.execution_time_ms:.2f} ms</p>
                                <pre>{json.dumps({'inputs': o.actual_metrics.get('inputs', {}), 'expected': expected, 'criteria': ac}, indent=2)}</pre>
                            </div>
                        </div>
                        <div>
                            {plot_img_html}
                        </div>
                    </div>
                </div>
            </td>
        </tr>
        """
        table_rows_html.append(row_html)

    table_rows_joined = "\n".join(table_rows_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SimuVerify Automated Validation Report</title>
    <style>
        :root {{
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --color-primary: #3b82f6;
            --color-success: #10b981;
            --color-danger: #ef4444;
            --color-warning: #f59e0b;
            --color-purple: #8b5cf6;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            line-height: 1.5;
            padding: 24px;
        }}

        .container {{ max-width: 1350px; margin: 0 auto; }}

        /* Header */
        header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px 32px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }}
        .header-top {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }}
        h1 {{ font-size: 26px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 12px; }}
        h1 span {{ color: var(--color-primary); }}
        .header-meta {{ color: var(--text-muted); font-size: 13px; margin-top: 6px; }}

        /* Environment Banner */
        .banner {{
            border-radius: 8px;
            padding: 14px 20px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 14px;
        }}
        .banner-ci {{
            background-color: rgba(59, 130, 246, 0.12);
            border: 1px solid rgba(59, 130, 246, 0.35);
            color: #93c5fd;
        }}
        .banner-matlab {{
            background-color: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #a7f3d0;
        }}
        .banner-tag {{
            background: #1e3a8a;
            color: #fff;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 4px;
            white-space: nowrap;
        }}

        /* KPI Cards Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }}
        .kpi-card::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
        }}
        .kpi-total::before {{ background: var(--color-primary); }}
        .kpi-pass::before {{ background: var(--color-success); }}
        .kpi-fail::before {{ background: var(--color-danger); }}
        .kpi-error::before {{ background: var(--color-warning); }}
        .kpi-rate::before {{ background: var(--color-purple); }}

        .kpi-title {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; }}
        .kpi-value {{ font-size: 32px; font-weight: 800; margin-top: 8px; color: #fff; }}
        .kpi-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}

        /* Progress Bar */
        .progress-box {{
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 24px;
        }}
        .progress-header {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 8px; font-weight: 600; }}
        .progress-bar {{
            height: 12px;
            background-color: #334155;
            border-radius: 6px;
            overflow: hidden;
            display: flex;
        }}
        .progress-pass {{ background-color: var(--color-success); }}
        .progress-fail {{ background-color: var(--color-danger); }}
        .progress-error {{ background-color: var(--color-warning); }}

        /* Filter Controls */
        .controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 16px;
        }}
        .filter-group {{ display: flex; gap: 8px; }}
        .filter-btn {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{ background: var(--bg-card-hover); }}
        .filter-btn.active {{ background: var(--color-primary); border-color: var(--color-primary); color: #fff; }}

        /* Results Table */
        .table-container {{
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
        th {{
            background-color: #0f172a;
            color: var(--text-muted);
            font-weight: 600;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 14px 16px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }}
        tr.test-row {{ cursor: pointer; transition: background 0.15s; }}
        tr.test-row:hover {{ background-color: var(--bg-card-hover); }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .badge-pass {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }}
        .badge-fail {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .badge-error {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}

        .badge-sev-critical {{ background: #7f1d1d; color: #fecaca; }}
        .badge-sev-major {{ background: #7c2d12; color: #fed7aa; }}
        .badge-sev-minor {{ background: #1e3a8a; color: #bfdbfe; }}

        .badge-cat-nominal {{ background: #064e3b; color: #a7f3d0; }}
        .badge-cat-boundary {{ background: #312e81; color: #c7d2fe; }}
        .badge-cat-fault-abnormal {{ background: #701a75; color: #f5d0fe; }}
        .badge-cat-invalid-config {{ background: #4c1d95; color: #ddd6fe; }}

        .font-mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
        .font-bold {{ font-weight: 700; }}

        .btn-toggle {{
            background: #334155;
            border: none;
            color: #cbd5e1;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
        }}

        /* Details Drawer */
        .details-row td {{ padding: 0; background: #0b1120; }}
        .details-card {{ padding: 24px; border-bottom: 2px solid var(--border); }}
        .grid-2col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 900px) {{ .grid-2col {{ grid-template-columns: 1fr; }} }}

        .failure-callout {{
            background-color: rgba(239, 68, 68, 0.15);
            border-left: 4px solid var(--color-danger);
            border-radius: 6px;
            padding: 16px 20px;
            margin-bottom: 20px;
        }}
        .failure-callout h4 {{ color: #f87171; font-size: 14px; margin-bottom: 8px; }}
        .failure-callout ul {{ margin-left: 20px; color: #fecaca; font-size: 13px; }}

        .checks-list {{ margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }}
        .check-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
        }}
        .check-pass {{ background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); color: #34d399; }}
        .check-fail {{ background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); color: #f87171; }}
        .check-icon {{ font-weight: bold; font-size: 14px; }}
        .check-name {{ font-weight: 700; }}
        .check-rule {{ font-family: monospace; }}
        .check-msg {{ color: var(--text-muted); }}

        .spec-box {{
            background: #1e293b;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 12px;
            margin-top: 8px;
            font-size: 12px;
        }}
        .spec-box pre {{
            max-height: 140px;
            overflow-y: auto;
            color: #94a3b8;
            font-size: 11px;
            margin-top: 8px;
        }}

        .plot-container {{
            background: #1e293b;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .plot-container h4 {{ font-size: 13px; color: var(--text-muted); margin-bottom: 12px; text-align: left; }}
        .plot-img {{ max-width: 100%; height: auto; border-radius: 6px; border: 1px solid #334155; }}

        footer {{
            text-align: center;
            margin-top: 40px;
            color: var(--text-muted);
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-top">
                <div>
                    <h1><span>SimuVerify</span> Automated Testing & Validation Report</h1>
                    <div class="header-meta">
                        Suite: <strong>{result.suite_name}</strong> (v{result.suite_version}) &nbsp;|&nbsp;
                        Generated: <strong>{result.timestamp}</strong> &nbsp;|&nbsp;
                        Execution Duration: <strong>{result.total_duration_ms:.2f} ms</strong>
                    </div>
                </div>
            </div>
        </header>

        <div class="banner {banner_class}">
            <span class="banner-tag">{banner_badge}</span>
            <div>{banner_desc}</div>
        </div>

        <!-- KPI Metrics -->
        <div class="kpi-grid">
            <div class="kpi-card kpi-total">
                <div class="kpi-title">Total Tests</div>
                <div class="kpi-value">{result.total_tests}</div>
                <div class="kpi-sub">Configured scenarios</div>
            </div>
            <div class="kpi-card kpi-pass">
                <div class="kpi-title">Passed</div>
                <div class="kpi-value" style="color: var(--color-success);">{result.passed_tests}</div>
                <div class="kpi-sub">Within tolerance limits</div>
            </div>
            <div class="kpi-card kpi-fail">
                <div class="kpi-title">Failed</div>
                <div class="kpi-value" style="color: var(--color-danger);">{result.failed_tests}</div>
                <div class="kpi-sub">Breached criteria (e.g. overload/gain)</div>
            </div>
            <div class="kpi-card kpi-error">
                <div class="kpi-title">Execution Errors</div>
                <div class="kpi-value" style="color: var(--color-warning);">{result.error_tests}</div>
                <div class="kpi-sub">Invalid config / schema traps</div>
            </div>
            <div class="kpi-card kpi-rate">
                <div class="kpi-title">Pass Rate</div>
                <div class="kpi-value" style="color: var(--color-purple);">{result.pass_percentage:.1f}%</div>
                <div class="kpi-sub">{result.passed_tests} of {result.total_tests} scenarios</div>
            </div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-box">
            <div class="progress-header">
                <span>Verification Outcome Distribution</span>
                <span>{result.passed_tests} PASS / {result.failed_tests} FAIL / {result.error_tests} ERROR</span>
            </div>
            <div class="progress-bar">
                <div class="progress-pass" style="width: {result.pass_percentage}%;"></div>
                <div class="progress-fail" style="width: {(result.failed_tests / result.total_tests * 100.0) if result.total_tests else 0}%;"></div>
                <div class="progress-error" style="width: {(result.error_tests / result.total_tests * 100.0) if result.total_tests else 0}%;"></div>
            </div>
        </div>

        <!-- Filter Controls -->
        <div class="controls">
            <div class="filter-group">
                <button class="filter-btn active" onclick="filterTable('all')">All ({result.total_tests})</button>
                <button class="filter-btn" onclick="filterTable('pass')">Passed ({result.passed_tests})</button>
                <button class="filter-btn" onclick="filterTable('fail')">Failed ({result.failed_tests})</button>
                <button class="filter-btn" onclick="filterTable('error')">Errors ({result.error_tests})</button>
            </div>
            <div style="font-size: 13px; color: var(--text-muted);">
                Click on any test row to expand diagnostic traces and simulation curves.
            </div>
        </div>

        <!-- Results Table -->
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Test ID</th>
                        <th>Scenario Name</th>
                        <th>Category</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Speed (Act / Exp)</th>
                        <th>Overshoot</th>
                        <th>Settling Time</th>
                        <th>Peak Current</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="tests-table-body">
                    {table_rows_joined}
                </tbody>
            </table>
        </div>

        <footer>
            SimuVerify Framework &bull; Designed for MATLAB/Simulink Automated Model Verification &bull; Continuous Integration Ready
        </footer>
    </div>

    <script>
        function toggleDetails(testId) {{
            const detailsRow = document.getElementById('details-' + testId);
            if (!detailsRow) return;
            if (detailsRow.style.display === 'none' || detailsRow.style.display === '') {{
                detailsRow.style.display = 'table-row';
            }} else {{
                detailsRow.style.display = 'none';
            }}
        }}

        function filterTable(filter) {{
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');

            const rows = document.querySelectorAll('tr.test-row');
            rows.forEach(r => {{
                const testId = r.querySelector('td').innerText.trim();
                const detailsRow = document.getElementById('details-' + testId);

                if (filter === 'all') {{
                    r.style.display = '';
                }} else if (r.classList.contains('status-' + filter)) {{
                    r.style.display = '';
                }} else {{
                    r.style.display = 'none';
                    if (detailsRow) detailsRow.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""

    path.write_text(html_content, encoding="utf-8")
    return path
