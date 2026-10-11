"""
DC Motor Simulation Engine (Deterministic Python Verification Model)
====================================================================
Simulates an electromechanical DC motor coupled to an inertia load with
a closed-loop PID speed controller and external load torque disturbances.

Physical Dynamics:
  L * di/dt + R * i = V - Ke * omega
  J * domega/dt + B * omega = Kt * i - tau_load

Where:
  - i(t) is armature current (A)
  - omega(t) is rotor angular velocity (rad/s)
  - V(t) is applied armature voltage from the PID controller (V)
  - tau_load(t) is the external load torque disturbance (N*m)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class SimulationResult:
    """Encapsulates full simulation time-series and computed validation metrics."""
    time: np.ndarray
    speed: np.ndarray
    current: np.ndarray
    voltage: np.ndarray
    target_speed: float
    metrics: Dict[str, float]
    raw_inputs: Dict[str, Any]
    source: str = "SimuVerify Deterministic Python Engine (CI Mode)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_speed": self.target_speed,
            "metrics": self.metrics,
            "source": self.source,
            "num_samples": len(self.time),
            "sim_duration_s": float(self.time[-1]) if len(self.time) > 0 else 0.0,
        }


class DCMotorSimulator:
    """
    Solves electromechanical motor differential equations with Runge-Kutta 4 (RK4) integration.
    """

    def __init__(
        self,
        resistance: float = 0.5,      # Ohms
        inductance: float = 0.02,     # Henries
        torque_const: float = 0.1,    # N*m / A
        back_emf_const: float = 0.1,  # V / (rad/s)
        max_voltage: float = 24.0,    # V (actuator limit)
        max_current: float = 12.0,    # A (drive current limit)
    ):
        self.R = float(resistance)
        self.L = float(inductance)
        self.Kt = float(torque_const)
        self.Ke = float(back_emf_const)
        self.V_max = float(max_voltage)
        self.I_max = float(max_current)

    def simulate(self, inputs: Dict[str, Any]) -> SimulationResult:
        """
        Executes a dynamic simulation given configuration input parameters.
        Raises ValueError for invalid physical parameters or numerical instability.
        """
        target_speed = float(inputs.get("target_speed", 100.0))
        load_torque = float(inputs.get("load_torque", 0.0))
        load_step_time = float(inputs.get("load_step_time", 2.0))
        sim_time = float(inputs.get("sim_time", 4.0))
        dt = float(inputs.get("sample_time", 0.001))

        kp = float(inputs.get("kp", 2.5))
        ki = float(inputs.get("ki", 5.0))
        kd = float(inputs.get("kd", 0.1))

        J = float(inputs.get("inertia", 0.01))
        B = float(inputs.get("friction", 0.005))

        if sim_time <= 0:
            raise ValueError(f"Simulation duration must be > 0, received {sim_time}")
        if dt <= 0 or dt > 0.05:
            raise ValueError(f"Sample step dt must be in (0, 0.05], received {dt}")
        if J <= 0:
            raise ValueError(f"Rotor inertia must be positive, received {J}")

        num_steps = int(math.ceil(sim_time / dt)) + 1
        t = np.linspace(0.0, sim_time, num_steps)

        # Preallocate time-series arrays
        current = np.zeros(num_steps, dtype=np.float64)
        speed = np.zeros(num_steps, dtype=np.float64)
        voltage = np.zeros(num_steps, dtype=np.float64)

        # Controller state variables
        integral_error = 0.0
        prev_error = target_speed - speed[0]

        # Derivatives function for motor electrical and mechanical state: [i, omega]
        def derivatives(state: np.ndarray, v_applied: float, t_load: float) -> np.ndarray:
            curr_i, curr_w = state[0], state[1]
            di_dt = (v_applied - self.R * curr_i - self.Ke * curr_w) / self.L
            dw_dt = (self.Kt * curr_i - B * curr_w - t_load) / J
            return np.array([di_dt, dw_dt], dtype=np.float64)

        state = np.array([0.0, 0.0], dtype=np.float64)  # Initial [current, speed]

        for k in range(num_steps - 1):
            curr_t = t[k]
            curr_i = state[0]
            curr_w = state[1]

            # Disturbance torque evaluation
            t_ext = load_torque if curr_t >= load_step_time else 0.0

            # PID Control calculation
            error = target_speed - curr_w
            d_error = (error - prev_error) / dt

            # Calculate raw PID voltage
            v_unsaturated = kp * error + ki * integral_error + kd * d_error

            # Saturation clamping [-V_max, +V_max]
            v_sat = max(-self.V_max, min(self.V_max, v_unsaturated))

            # Motor drive current limiter
            v_curr_max = self.R * self.I_max + self.Ke * curr_w
            v_curr_min = -self.R * self.I_max + self.Ke * curr_w
            v_effective = max(v_curr_min, min(v_curr_max, v_sat))
            voltage[k] = v_effective

            # Anti-windup clamping: only integrate if not saturating
            if abs(v_unsaturated - v_effective) < 1e-4 or (v_unsaturated > self.V_max and error < 0) or (v_unsaturated < -self.V_max and error > 0):
                integral_error += error * dt

            prev_error = error

            # RK4 Integration step
            k1 = derivatives(state, v_effective, t_ext)
            k2 = derivatives(state + 0.5 * dt * k1, v_effective, t_ext)
            k3 = derivatives(state + 0.5 * dt * k2, v_effective, t_ext)
            k4 = derivatives(state + dt * k3, v_effective, t_ext)

            state = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

            # Check for numerical explosion / instability
            if np.isnan(state[0]) or np.isnan(state[1]) or abs(state[1]) > 1e6:
                raise FloatingPointError("Numerical instability detected during motor integration")

            current[k + 1] = state[0]
            speed[k + 1] = state[1]

        # Final step voltage
        voltage[-1] = voltage[-2]

        # Compute validation metrics
        metrics = self._compute_performance_metrics(t, speed, current, target_speed)

        return SimulationResult(
            time=t,
            speed=speed,
            current=current,
            voltage=voltage,
            target_speed=target_speed,
            metrics=metrics,
            raw_inputs=inputs,
            source="SimuVerify Deterministic Python Engine (CI Mode)",
        )

    def _compute_performance_metrics(
        self,
        time: np.ndarray,
        speed: np.ndarray,
        current: np.ndarray,
        target_speed: float,
    ) -> Dict[str, float]:
        """Calculates standard control system time-domain metrics."""
        # Steady-state speed: average over final 10% of simulation window
        tail_idx = int(0.9 * len(speed))
        steady_state_speed = float(np.mean(speed[tail_idx:]))

        # Steady-state error
        steady_state_error = float(abs(target_speed - steady_state_speed))

        # Peak and overshoot
        peak_speed = float(np.max(speed))
        if target_speed > 0:
            overshoot_pct = float(max(0.0, ((peak_speed - target_speed) / target_speed) * 100.0))
        else:
            overshoot_pct = 0.0

        # Settling time (2% envelope of steady-state value)
        settling_band = 0.02 * max(abs(steady_state_speed), 1.0)
        outside_band = np.where(np.abs(speed - steady_state_speed) > settling_band)[0]
        if len(outside_band) == 0:
            settling_time_s = 0.0
        elif outside_band[-1] >= len(time) - 1:
            settling_time_s = float(time[-1])  # Has not settled by end
        else:
            settling_time_s = float(time[outside_band[-1] + 1])

        # Rise time (10% to 90% of steady-state speed)
        t_10_arr = np.where(speed >= 0.1 * steady_state_speed)[0]
        t_90_arr = np.where(speed >= 0.9 * steady_state_speed)[0]
        if len(t_10_arr) > 0 and len(t_90_arr) > 0 and t_90_arr[0] >= t_10_arr[0]:
            rise_time_s = float(time[t_90_arr[0]] - time[t_10_arr[0]])
        else:
            rise_time_s = float(time[-1])

        # Peak current
        peak_current_a = float(np.max(np.abs(current)))

        return {
            "steady_state_speed": round(steady_state_speed, 4),
            "steady_state_error": round(steady_state_error, 4),
            "peak_speed": round(peak_speed, 4),
            "overshoot_pct": round(overshoot_pct, 4),
            "settling_time_s": round(settling_time_s, 4),
            "rise_time_s": round(rise_time_s, 4),
            "peak_current_a": round(peak_current_a, 4),
        }
