classdef ResultValidator < handle
% RESULTVALIDATOR Evaluates simulation outputs against acceptance criteria.
%
% Methods:
%   evaluate(testCase, simResult, execError, execTimeMs) -> outcome

    methods
        function outcome = evaluate(~, testCase, simResult, execError, execTimeMs)
            outcome = struct();
            outcome.test_id = testCase.id;
            outcome.name = testCase.name;
            outcome.category = testCase.category;
            outcome.severity = testCase.severity;
            outcome.execution_time_ms = execTimeMs;
            outcome.actual_metrics = struct();
            outcome.expected_values = testCase.expected;
            outcome.acceptance_criteria = testCase.acceptance_criteria;
            outcome.failure_reasons = {};
            outcome.source = 'None';

            % 1. Handle Execution / Configuration Errors
            if ~isempty(execError) || isempty(simResult)
                outcome.status = 'ERROR';
                if isempty(execError)
                    outcome.failure_reasons = {'Simulation produced no output'};
                else
                    outcome.failure_reasons = {['Execution Exception: ' execError]};
                end
                return;
            end

            outcome.source = simResult.source;
            metrics = simResult.metrics;
            outcome.actual_metrics = metrics;

            ac = testCase.acceptance_criteria;
            exp = testCase.expected;
            reasons = {};

            % 2. Check Steady-State Speed Absolute Tolerance
            if isfield(ac, 'speed_tolerance_abs') && isfield(exp, 'steady_state_speed')
                target = exp.steady_state_speed;
                tol = ac.speed_tolerance_abs;
                actual = metrics.steady_state_speed;
                diff = abs(actual - target);
                if diff > tol
                    reasons{end+1} = sprintf('Steady-state speed %.2f rad/s exceeded absolute tolerance +-%.2f from target %.2f', ...
                        actual, tol, target);
                end
            end

            % 3. Check Steady-State Speed Percentage Tolerance
            if isfield(ac, 'speed_tolerance_pct') && isfield(exp, 'steady_state_speed')
                target = exp.steady_state_speed;
                tol_pct = ac.speed_tolerance_pct;
                actual = metrics.steady_state_speed;
                diff_pct = (abs(actual - target) / target) * 100.0;
                if diff_pct > tol_pct
                    reasons{end+1} = sprintf('Steady-state speed error %.2f%% exceeded allowable percentage %.2f%%', ...
                        diff_pct, tol_pct);
                end
            end

            % 4. Check Maximum Overshoot
            if isfield(ac, 'max_overshoot_pct')
                limit = ac.max_overshoot_pct;
                actual = metrics.overshoot_pct;
                if actual > limit
                    reasons{end+1} = sprintf('Peak overshoot %.2f%% exceeded maximum allowable limit %.2f%%', ...
                        actual, limit);
                end
            end

            % 5. Check Maximum Settling Time
            if isfield(ac, 'max_settling_time_s')
                limit = ac.max_settling_time_s;
                actual = metrics.settling_time_s;
                if actual > limit
                    reasons{end+1} = sprintf('Settling time %.3f s exceeded maximum allowable time %.3f s', ...
                        actual, limit);
                end
            end

            % 6. Check Maximum Steady-State Error
            if isfield(ac, 'max_steady_state_error')
                limit = ac.max_steady_state_error;
                actual = metrics.steady_state_error;
                if actual > limit
                    reasons{end+1} = sprintf('Steady-state tracking error %.3f rad/s exceeded limit %.3f rad/s', ...
                        actual, limit);
                end
            end

            % 7. Check Peak Transient Current
            if isfield(ac, 'max_peak_current_a')
                limit = ac.max_peak_current_a;
                actual = metrics.peak_current_a;
                if actual > limit
                    reasons{end+1} = sprintf('Peak transient current %.2f A exceeded electrical safety threshold %.2f A', ...
                        actual, limit);
                end
            end

            outcome.failure_reasons = reasons;
            if isempty(reasons)
                outcome.status = 'PASS';
            else
                outcome.status = 'FAIL';
            end
        end
    end
end
