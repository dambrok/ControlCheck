"""
Unit Tests for DC Motor Dynamic Simulation Engine
"""

import numpy as np
import pytest
from simuverify.engine.simulator import DCMotorSimulator


@pytest.fixture
def sim():
    return DCMotorSimulator()


def test_nominal_step_response(sim):
    inputs = {
        "target_speed": 100.0,
        "load_torque": 0.0,
        "load_step_time": 2.0,
        "sim_time": 3.0,
        "sample_time": 0.001,
        "kp": 2.5,
        "ki": 5.0,
        "kd": 0.1,
    }
    result = sim.simulate(inputs)

    assert result.target_speed == 100.0
    assert len(result.time) == len(result.speed)
    assert result.time[-1] == pytest.approx(3.0, rel=1e-3)

    # Steady state speed should be close to 100 rad/s
    metrics = result.metrics
    assert metrics["steady_state_speed"] == pytest.approx(100.0, abs=1.5)
    assert metrics["overshoot_pct"] < 12.0
    assert metrics["settling_time_s"] < 1.5
    assert metrics["peak_current_a"] < 15.0


def test_disturbance_rejection(sim):
    # With integral control, speed should recover despite load torque
    inputs = {
        "target_speed": 80.0,
        "load_torque": 0.5,
        "load_step_time": 1.5,
        "sim_time": 3.5,
        "sample_time": 0.001,
        "kp": 2.5,
        "ki": 5.0,
        "kd": 0.1,
    }
    result = sim.simulate(inputs)
    metrics = result.metrics

    # Steady-state should still reach ~80 rad/s
    assert metrics["steady_state_speed"] == pytest.approx(80.0, abs=2.0)
    assert metrics["steady_state_error"] < 2.0


def test_voltage_saturation_limit(sim):
    # When requesting very high speed, applied voltage should not exceed V_max (24V)
    inputs = {
        "target_speed": 220.0,
        "load_torque": 0.0,
        "sim_time": 2.0,
        "sample_time": 0.001,
        "kp": 10.0,
        "ki": 5.0,
        "kd": 0.0,
    }
    result = sim.simulate(inputs)
    assert np.all(result.voltage <= 24.0 + 1e-6)
    assert np.all(result.voltage >= -24.0 - 1e-6)


def test_invalid_parameters_raise_value_error(sim):
    with pytest.raises(ValueError, match="Simulation duration must be > 0"):
        sim.simulate({"sim_time": -1.0})

    with pytest.raises(ValueError, match="Sample step dt must be in"):
        sim.simulate({"sample_time": 0.0})

    with pytest.raises(ValueError, match="Rotor inertia must be positive"):
        sim.simulate({"inertia": -0.05})
