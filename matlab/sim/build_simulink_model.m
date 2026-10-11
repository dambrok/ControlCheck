function modelPath = build_simulink_model(targetDir)
% BUILD_SIMULINK_MODEL Programmatically constructs the original DC Motor Simulink Model
%
% Syntax:
%   modelPath = build_simulink_model(targetDir)
%
% Description:
%   Constructs an original Simulink block diagram for DC Motor Closed-Loop
%   Speed Control using native Simulink APIs (new_system, add_block, add_line).
%   Saves the resulting model as 'dc_motor_control.slx' inside the targetDir.
%
% Inputs:
%   targetDir - String path where model should be saved [default: 'models']
%
% Outputs:
%   modelPath - String path to the created .slx file
%
% Notes:
%   Requires an active MATLAB and Simulink installation.
%   If Simulink is not licensed on the host, this function exits cleanly with
%   an informative notice and does not create corrupted dummy files.

    if nargin < 1 || isempty(targetDir)
        thisDir = fileparts(mfilename('fullpath'));
        targetDir = fullfile(thisDir, '..', '..', 'models');
    end

    if ~exist(targetDir, 'dir')
        mkdir(targetDir);
    end

    % Verify Simulink availability
    if ~exist('simulink', 'file') && ~license('test', 'SIMULINK')
        warning('SimuVerify:SimulinkUnavailable', ...
            ['Simulink is not licensed or available in this MATLAB environment. ' ...
             'The framework will use the pure MATLAB ODE simulator (dc_motor_model.m).']);
        modelPath = '';
        return;
    end

    modelName = 'dc_motor_control';
    modelPath = fullfile(targetDir, [modelName '.slx']);

    % Close if already open
    if bdIsLoaded(modelName)
        close_system(modelName, 0);
    end

    fprintf('[*] Constructing Simulink model: %s\n', modelName);
    new_system(modelName);
    open_system(modelName);

    try
        % Configure Solver
        set_param(modelName, 'SolverType', 'Fixed-step');
        set_param(modelName, 'Solver', 'ode4');
        set_param(modelName, 'FixedStep', '0.001');
        set_param(modelName, 'StopTime', '4.0');
        set_param(modelName, 'SaveTime', 'on');
        set_param(modelName, 'TimeSaveName', 'tout');
        set_param(modelName, 'SaveOutput', 'on');
        set_param(modelName, 'OutputSaveName', 'yout');

        % Add Reference Step Input (Target Speed)
        add_block('simulink/Sources/Step', [modelName '/Target_Speed_Step'], ...
            'Position', [40, 80, 70, 110], ...
            'Time', '0.0', ...
            'Before', '0.0', ...
            'After', '100.0');

        % Add Sum block for tracking error
        add_block('simulink/Math Operations/Sum', [modelName '/Sum_Error'], ...
            'Position', [130, 85, 150, 105], ...
            'Inputs', '|+-');

        % Add PID Controller (Continuous)
        add_block('simulink/Continuous/PID Controller', [modelName '/PID_Controller'], ...
            'Position', [200, 77, 240, 113], ...
            'P', '2.5', ...
            'I', '5.0', ...
            'D', '0.1');

        % Add Saturation (Voltage Limits: +/- 24V)
        add_block('simulink/Discontinuities/Saturation', [modelName '/Voltage_Saturation'], ...
            'Position', [290, 80, 320, 110], ...
            'UpperLimit', '24.0', ...
            'LowerLimit', '-24.0');

        % Add Motor Armature Subsystem / Transfer Function (Electrical: 1 / (L*s + R))
        % L = 0.02 H, R = 0.5 Ohm
        add_block('simulink/Continuous/Transfer Fcn', [modelName '/Armature_Dynamics'], ...
            'Position', [380, 77, 460, 113], ...
            'Numerator', '[1]', ...
            'Denominator', '[0.02 0.5]');

        % Add Torque Constant Kt = 0.1
        add_block('simulink/Math Operations/Gain', [modelName '/Kt_Gain'], ...
            'Position', [510, 80, 540, 110], ...
            'Gain', '0.1');

        % Add Disturbance Torque Input Step
        add_block('simulink/Sources/Step', [modelName '/Load_Torque_Step'], ...
            'Position', [510, 160, 540, 190], ...
            'Time', '2.0', ...
            'Before', '0.0', ...
            'After', '0.0');

        % Add Sum block for Mechanical Torque
        add_block('simulink/Math Operations/Sum', [modelName '/Sum_Torque'], ...
            'Position', [590, 85, 610, 105], ...
            'Inputs', '|+-');

        % Add Mechanical Dynamics (1 / (J*s + B))
        % J = 0.01 kg*m^2, B = 0.005 N*m*s/rad
        add_block('simulink/Continuous/Transfer Fcn', [modelName '/Mechanical_Dynamics'], ...
            'Position', [660, 77, 740, 113], ...
            'Numerator', '[1]', ...
            'Denominator', '[0.01 0.005]');

        % Add Back-EMF Gain Ke = 0.1
        add_block('simulink/Math Operations/Gain', [modelName '/Ke_BackEMF'], ...
            'Position', [500, 240, 530, 270], ...
            'Gain', '0.1', ...
            'Orientation', 'left');

        % Add Outport for Speed (rad/s)
        add_block('simulink/Sinks/Out1', [modelName '/Motor_Speed_Out'], ...
            'Position', [810, 85, 840, 105]);

        % Add Outport for Current (A)
        add_block('simulink/Sinks/Out1', [modelName '/Armature_Current_Out'], ...
            'Position', [510, 30, 540, 50]);

        % Connect Signals
        add_line(modelName, 'Target_Speed_Step/1', 'Sum_Error/1');
        add_line(modelName, 'Sum_Error/1', 'PID_Controller/1');
        add_line(modelName, 'PID_Controller/1', 'Voltage_Saturation/1');
        add_line(modelName, 'Voltage_Saturation/1', 'Armature_Dynamics/1');
        add_line(modelName, 'Armature_Dynamics/1', 'Kt_Gain/1');
        add_line(modelName, 'Armature_Dynamics/1', 'Armature_Current_Out/1');
        add_line(modelName, 'Kt_Gain/1', 'Sum_Torque/1');
        add_line(modelName, 'Load_Torque_Step/1', 'Sum_Torque/2');
        add_line(modelName, 'Sum_Torque/1', 'Mechanical_Dynamics/1');
        add_line(modelName, 'Mechanical_Dynamics/1', 'Motor_Speed_Out/1');

        % Feedback loops
        add_line(modelName, 'Mechanical_Dynamics/1', 'Ke_BackEMF/1');
        add_line(modelName, 'Mechanical_Dynamics/1', 'Sum_Error/2');

        % Save system
        save_system(modelName, modelPath);
        close_system(modelName);
        fprintf('[+] Successfully built and saved: %s\n', modelPath);

    catch buildErr
        if bdIsLoaded(modelName)
            close_system(modelName, 0);
        end
        rethrow(buildErr);
    end
end
