"""
Plot Generation Engine
======================
Generates time-domain response curves (Speed vs Time, Current vs Time) with
reference setpoints and tolerance envelopes for engineering inspection.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Dict, Optional, Tuple
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless CI
import matplotlib.pyplot as plt
import numpy as np
from simuverify.engine.simulator import SimulationResult
from simuverify.engine.validator import TestOutcome


def plot_test_response(
    test_id: str,
    sim_result: SimulationResult,
    outcome: Optional[TestOutcome] = None,
    save_path: Optional[Path | str] = None,
) -> Tuple[plt.Figure, str]:
    """
    Plots angular speed and current traces for a given simulation result.
    Returns (Figure, base64_png_string).
    """
    t = sim_result.time
    w = sim_result.speed
    i = sim_result.current
    target = sim_result.target_speed

    fig, (ax_w, ax_i) = plt.subplots(2, 1, figsize=(8.5, 4.8), sharex=True, dpi=120)

    # Status color theme
    status = outcome.status if outcome else "INFO"
    status_color = "#10B981" if status == "PASS" else ("#EF4444" if status == "FAIL" else "#F59E0B")

    # 1. Angular Velocity Plot
    ax_w.plot(t, w, label="Measured Speed \u03c9(t)", color="#2563EB", linewidth=2.0)
    ax_w.axhline(target, color="#DC2626", linestyle="--", linewidth=1.5, label=f"Target ({target:.1f} rad/s)")

    # Show tolerance band if outcome contains criteria
    if outcome and "speed_tolerance_abs" in outcome.acceptance_criteria:
        tol = float(outcome.acceptance_criteria["speed_tolerance_abs"])
        ax_w.fill_between(
            t,
            target - tol,
            target + tol,
            color="#10B981",
            alpha=0.15,
            label=f"Tolerance Band (\u00b1{tol:.1f} rad/s)",
        )

    ax_w.set_ylabel("Speed (rad/s)", fontsize=10, fontweight="bold")
    ax_w.set_title(
        f"{test_id}: {outcome.name if outcome else ''}  [{status}]",
        fontsize=11,
        fontweight="bold",
        color=status_color,
    )
    ax_w.grid(True, linestyle=":", alpha=0.6)
    ax_w.legend(loc="lower right", fontsize=8)

    # 2. Armature Current Plot
    ax_i.plot(t, i, label="Armature Current i(t)", color="#D97706", linewidth=1.6)
    if outcome and "max_peak_current_a" in outcome.acceptance_criteria:
        i_lim = float(outcome.acceptance_criteria["max_peak_current_a"])
        ax_i.axhline(i_lim, color="#991B1B", linestyle=":", linewidth=1.2, label=f"Max Limit ({i_lim:.1f} A)")
        ax_i.axhline(-i_lim, color="#991B1B", linestyle=":", linewidth=1.2)

    ax_i.set_xlabel("Time (seconds)", fontsize=10, fontweight="bold")
    ax_i.set_ylabel("Current (A)", fontsize=10, fontweight="bold")
    ax_i.grid(True, linestyle=":", alpha=0.6)
    ax_i.legend(loc="upper right", fontsize=8)

    fig.tight_layout()

    # Save to file if requested
    if save_path:
        out_p = Path(save_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_p, dpi=150, bbox_inches="tight")

    # Encode to base64 for direct inline HTML inclusion
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    base64_str = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return fig, base64_str


def generate_all_plots(
    sim_traces: Dict[str, SimulationResult],
    outcomes: Dict[str, TestOutcome],
    plots_dir: Path | str,
) -> Dict[str, str]:
    """Generates PNG images on disk and returns base64 dictionary keyed by test_id."""
    p_dir = Path(plots_dir)
    p_dir.mkdir(parents=True, exist_ok=True)

    encoded_plots: Dict[str, str] = {}
    for test_id, trace in sim_traces.items():
        outcome = outcomes.get(test_id)
        img_file = p_dir / f"{test_id}_response.png"
        _, b64 = plot_test_response(test_id, trace, outcome=outcome, save_path=img_file)
        encoded_plots[test_id] = b64

    return encoded_plots
