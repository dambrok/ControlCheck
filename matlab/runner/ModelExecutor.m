classdef ModelExecutor < handle
% MODELEXECUTOR Decouples model/simulation execution from result evaluation.
%
% Methods:
%   execute(testCase) - Runs the model for a given testCase inputs struct.
%                       Catches errors gracefully and returns [simResult, errorMsg].

    methods
        function [simResult, errorMsg] = execute(~, testCase)
            simResult = [];
            errorMsg = '';

            try
                inputs = testCase.inputs;
                % Call simulation harness (Simulink if available, else ODE)
                simResult = run_simulink_model(inputs);
            catch err
                errorMsg = sprintf('%s: %s', err.identifier, err.message);
            end
        end
    end
end
