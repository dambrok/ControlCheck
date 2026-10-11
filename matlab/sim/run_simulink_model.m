function result = run_simulink_model(inputs)
% RUN_SIMULINK_MODEL Executes the DC Motor simulation via Simulink or ODE fallback
%
% Syntax:
%   result = run_simulink_model(inputs)
%
% Description:
%   Executes the DC Motor Speed Control model. If Simulink is installed and
%   the model exists, it executes 'sim()'. If Simulink is unavailable, it
%   transparently executes the pure MATLAB ODE solver (dc_motor_model.m).
%   The execution source is explicitly labelled in the output structure.
%
% Inputs:
%   inputs - Struct of scenario inputs (target_speed, load_torque, etc.)
%
% Outputs:
%   result - Struct with fields: time, speed, current, metrics, source

    if nargin < 1 || isempty(inputs)
        inputs = struct();
    end

    thisDir = fileparts(mfilename('fullpath'));
    modelFile = fullfile(thisDir, '..', '..', 'models', 'dc_motor_control.slx');

    hasSimulink = (exist('simulink', 'file') || license('test', 'SIMULINK')) && exist('sim', 'file');

    if hasSimulink && isfile(modelFile)
        try
            % Execute native Simulink model
            modelName = 'dc_motor_control';
            load_system(modelFile);

            % Configure scenario parameters
            simTime = 4.0;
            if isfield(inputs, 'sim_time') && ~isempty(inputs.sim_time)
                simTime = inputs.sim_time;
            end

            targetSpeed = 100.0;
            if isfield(inputs, 'target_speed') && ~isempty(inputs.target_speed)
                targetSpeed = inputs.target_speed;
            end

            set_param([modelName '/Target_Speed_Step'], 'After', num2str(targetSpeed));
            if isfield(inputs, 'load_torque')
                set_param([modelName '/Load_Torque_Step'], 'After', num2str(inputs.load_torque));
            end
            if isfield(inputs, 'load_step_time')
                set_param([modelName '/Load_Torque_Step'], 'Time', num2str(inputs.load_step_time));
            end

            simOut = sim(modelName, 'StopTime', num2str(simTime));

            % Extract outputs
            tout = simOut.tout;
            yout = simOut.yout;

            result = struct();
            result.time = tout;
            result.speed = yout(:, 1);
            result.current = yout(:, 2);
            result.target_speed = targetSpeed;
            result.source = 'Simulink Native (sim command)';
            result.metrics = compute_sim_metrics(tout, result.speed, result.current, targetSpeed);
            return;
        catch simErr
            warning('SimuVerify:SimulinkExecutionFailed', ...
                'Simulink run failed (%s). Falling back to MATLAB ODE solver.', simErr.message);
        end
    end

    % Transparent fallback to pure MATLAB ODE solver
    result = dc_motor_model(inputs);
end

function m = compute_sim_metrics(t, w, i, target)
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
