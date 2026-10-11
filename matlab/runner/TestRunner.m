classdef TestRunner < handle
% TESTRUNNER Orchestrates test suite execution and collects outcomes.
%
% Properties:
%   executor  - Instance of ModelExecutor
%   validator - Instance of ResultValidator
%
% Methods:
%   runSuite(suite) - Runs all cases and returns summary structure

    properties
        executor
        validator
    end

    methods
        function obj = TestRunner(executor, validator)
            if nargin < 1 || isempty(executor)
                obj.executor = ModelExecutor();
            else
                obj.executor = executor;
            end

            if nargin < 2 || isempty(validator)
                obj.validator = ResultValidator();
            else
                obj.validator = validator;
            end
        end

        function summary = runSuite(obj, suite)
            testCases = suite.test_cases;
            total = length(testCases);
            outcomes = cell(total, 1);

            fprintf('===========================================================================\n');
            fprintf('  SIMUVERIFY: MATLAB Test Suite Execution\n');
            fprintf('  Suite: %s\n', suite.suite_name);
            fprintf('===========================================================================\n');

            totalTimer = tic;

            for i = 1:total
                tc = testCases(i);
                t0 = tic;

                % Model execution
                [simResult, execError] = obj.executor.execute(tc);
                elapsedMs = toc(t0) * 1000.0;

                % Result evaluation
                outcome = obj.validator.evaluate(tc, simResult, execError, elapsedMs);
                outcomes{i} = outcome;

                % Display console progress
                fprintf(' [%02d/%02d] [%-5s] %-11s %-36s (%6.2f ms)\n', ...
                    i, total, outcome.status, outcome.test_id, outcome.name(1:min(36, end)), elapsedMs);

                if ~strcmp(outcome.status, 'PASS')
                    for r = 1:length(outcome.failure_reasons)
                        fprintf('         |-- Reason: %s\n', outcome.failure_reasons{r});
                    end
                end
            end

            totalDurationMs = toc(totalTimer) * 1000.0;

            % Tally stats
            passCount = 0;
            failCount = 0;
            errorCount = 0;
            for i = 1:total
                st = outcomes{i}.status;
                if strcmp(st, 'PASS')
                    passCount = passCount + 1;
                elseif strcmp(st, 'FAIL')
                    failCount = failCount + 1;
                else
                    errorCount = errorCount + 1;
                end
            end

            passPct = (passCount / total) * 100.0;

            summary = struct();
            summary.suite_name = suite.suite_name;
            summary.total_tests = total;
            summary.passed_tests = passCount;
            summary.failed_tests = failCount;
            summary.error_tests = errorCount;
            summary.pass_percentage = passPct;
            summary.total_duration_ms = totalDurationMs;
            summary.outcomes = outcomes;

            fprintf('===========================================================================\n');
            fprintf('  SUMMARY: %d Total | %d Passed | %d Failed | %d Errors (%.1f%% Pass Rate)\n', ...
                total, passCount, failCount, errorCount, passPct);
            fprintf('===========================================================================\n\n');
        end
    end
end
