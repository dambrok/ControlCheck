function result = dc_motor_model(inputs)
% DC_MOTOR_MODEL Pure MATLAB ODE solver for DC Motor Speed Control
%
% Syntax:
%   result = dc_motor_model(inputs)
%
% Inputs:
%   inputs - Struct with fields:
%     target_speed   - Reference velocity (rad/s) [default: 100.0]
%     load_torque    - External load disturbance (N*m) [default: 0.0]
%     load_step_time - Disturbance injection time (s) [default: 2.0]
%     sim_time       - Total simulation duration (s) [default: 4.0]
%     sample_time    - Time step dt (s) [default: 0.001]
%     kp, ki, kd     - PID controller gains
%     inertia        - Rotor inertia J (kg*m^2) [default: 0.01]
%     friction       - Viscous damping B (N*m*s/rad) [default: 0.005]
%
% Outputs:
%   result - Struct containing:
%     time, speed, current, voltage, metrics, target_speed, source
%
% Notes:
%   Does NOT require Simulink or Control System Toolbox.
%   Uses Runge-Kutta 4th Order (RK4) numerical integration.

    if nargin < 1 || isempty(inputs)
        inputs = struct();
    end

    % Extract parameters with defaults
    target_speed = get_param(inputs, 'target_speed', 100.0);
    load_torque = get_param(inputs, 'load_torque', 0.0);
    load_step_time = get_param(inputs, 'load_step_time', 2.0);
    sim_time = get_param(inputs, 'sim_time', 4.0);
    dt = get_param(inputs, 'sample_time', 0.001);

    kp = get_param(inputs, 'kp', 2.5);
    ki = get_param(inputs, 'ki', 5.0);
    kd = get_param(inputs, 'kd', 0.1);

    J = get_param(inputs, 'inertia', 0.01);
    B = get_param(inputs, 'friction', 0.005);

    % Physical Motor Constants
    R = 0.5;      % Armature Resistance (Ohms)
    L = 0.02;     % Armature Inductance (Henries)
    Kt = 0.1;     % Motor Torque Constant (N*m / A)
    Ke = 0.1;     % Back-EMF Constant (V / (rad/s))
    V_max = 24.0; % Voltage Saturation Limit (V)
    I_max = 12.0; % Drive Current Limit (A)

    if sim_time <= 0
        error('SimuVerify:InvalidDuration', 'Simulation time must be positive.');
    end

    num_steps = ceil(sim_time / dt) + 1;
    t = linspace(0.0, sim_time, num_steps);

    % Preallocate time-series
    current = zeros(1, num_steps);
    speed = zeros(1, num_steps);
    voltage = zeros(1, num_steps);

    integral_error = 0.0;
    prev_error = target_speed - speed(1);
    state = [0.0; 0.0]; % [current; angular_velocity]

    for k = 1:(num_steps - 1)
        curr_t = t(k);
        curr_i = state(1);
        curr_w = state(2);

        % External load disturbance step
        if curr_t >= load_step_time
            t_ext = load_torque;
        else
            t_ext = 0.0;
        end

        % PID Control computation
        error_val = target_speed - curr_w;
        d_error = (error_val - prev_error) / dt;

        v_unsaturated = kp * error_val + ki * integral_error + kd * d_error;

        % Saturation [-24V, +24V]
        v_sat = max(-V_max, min(V_max, v_unsaturated));

        % Motor drive current limiter
        v_curr_max = R * I_max + Ke * curr_w;
        v_curr_min = -R * I_max + Ke * curr_w;
        v_effective = max(v_curr_min, min(v_curr_max, v_sat));
        voltage(k) = v_effective;

        % Anti-windup clamping
        if abs(v_unsaturated - v_effective) < 1e-4 || ...
           (v_unsaturated > V_max && error_val < 0) || ...
           (v_unsaturated < -V_max && error_val > 0)
            integral_error = integral_error + error_val * dt;
        end

        prev_error = error_val;

        % RK4 Integration
        k1 = motor_derivatives(state, v_effective, t_ext, R, L, Ke, Kt, B, J);
        k2 = motor_derivatives(state + 0.5 * dt * k1, v_effective, t_ext, R, L, Ke, Kt, B, J);
        k3 = motor_derivatives(state + 0.5 * dt * k2, v_effective, t_ext, R, L, Ke, Kt, B, J);
        k4 = motor_derivatives(state + dt * k3, v_effective, t_ext, R, L, Ke, Kt, B, J);

        state = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4);

        current(k + 1) = state(1);
        speed(k + 1) = state(2);
    end

    voltage(num_steps) = voltage(num_steps - 1);

    % Compute Performance Metrics
    metrics = compute_metrics(t, speed, current, target_speed);

    result = struct();
    result.time = t;
    result.speed = speed;
    result.current = current;
    result.voltage = voltage;
    result.target_speed = target_speed;
    result.metrics = metrics;
    result.source = 'MATLAB Native ODE Solver (Deterministic RK4)';
end

function dxdt = motor_derivatives(x, V, tau_l, R, L, Ke, Kt, B, J)
    i_val = x(1);
    w_val = x(2);
    di_dt = (V - R * i_val - Ke * w_val) / L;
    dw_dt = (Kt * i_val - B * w_val - tau_l) / J;
    dxdt = [di_dt; dw_dt];
end

function val = get_param(s, fieldName, defaultVal)
    if isfield(s, fieldName) && ~isempty(s.(fieldName))
        val = s.(fieldName);
    else
        val = defaultVal;
    end
end

function m = compute_metrics(t, w, i, target)
    tail_idx = max(1, floor(0.9 * length(w)));
    steady_state_speed = mean(w(tail_idx:end));
    steady_state_error = abs(target - steady_state_speed);

    peak_speed = max(w);
    if target > 0
        overshoot_pct = max(0.0, ((peak_speed - target) / target) * 100.0);
    else
        overshoot_pct = 0.0;
    end

    settling_band = 0.02 * max(abs(steady_state_speed), 1.0);
    outside = find(abs(w - steady_state_speed) > settling_band);
    if isempty(outside)
        settling_time_s = 0.0;
    elseif outside(end) >= length(t)
        settling_time_s = t(end);
    else
        settling_time_s = t(outside(end) + 1);
    end

    peak_current_a = max(abs(i));

    m = struct();
    m.steady_state_speed = round(steady_state_speed, 4);
    m.steady_state_error = round(steady_state_error, 4);
    m.peak_speed = round(peak_speed, 4);
    m.overshoot_pct = round(overshoot_pct, 4);
    m.settling_time_s = round(settling_time_s, 4);
    m.peak_current_a = round(peak_current_a, 4);
end
