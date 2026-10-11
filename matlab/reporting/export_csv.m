function csvPath = export_csv(summary, outputPath)
% EXPORT_CSV Writes MATLAB validation outcomes to a CSV file.
%
% Syntax:
%   csvPath = export_csv(summary, outputPath)

    if nargin < 2 || isempty(outputPath)
        thisDir = fileparts(mfilename('fullpath'));
        outputPath = fullfile(thisDir, '..', '..', 'reports', 'validation_summary.csv');
    end

    [parentDir, ~, ~] = fileparts(outputPath);
    if ~exist(parentDir, 'dir')
        mkdir(parentDir);
    end

    fid = fopen(outputPath, 'w', 'n', 'UTF-8');
    if fid == -1
        error('SimuVerify:FileOpenError', 'Unable to create CSV file: %s', outputPath);
    end
    cleaner = onCleanup(@() fclose(fid));

    % Header row
    fprintf(fid, 'Test_ID,Test_Name,Category,Severity,Status,Execution_Time_ms,Target_Speed,Actual_Speed,Overshoot_Pct,Settling_Time_s,Peak_Current_A,Failure_Reasons,Execution_Source\n');

    outcomes = summary.outcomes;
    for i = 1:length(outcomes)
        o = outcomes{i};
        w_exp = 'N/A';
        if isfield(o.expected_values, 'steady_state_speed')
            w_exp = sprintf('%.2f', o.expected_values.steady_state_speed);
        end

        w_act = 'N/A';
        os_act = 'N/A';
        ts_act = 'N/A';
        i_act = 'N/A';
        if isfield(o.actual_metrics, 'steady_state_speed')
            w_act = sprintf('%.2f', o.actual_metrics.steady_state_speed);
            os_act = sprintf('%.2f', o.actual_metrics.overshoot_pct);
            ts_act = sprintf('%.3f', o.actual_metrics.settling_time_s);
            i_act = sprintf('%.2f', o.actual_metrics.peak_current_a);
        end

        reasonsStr = 'None';
        if ~isempty(o.failure_reasons)
            reasonsStr = strjoin(o.failure_reasons, ' | ');
            reasonsStr = strrep(reasonsStr, '"', '""');
            reasonsStr = ['"' reasonsStr '"'];
        end

        nameClean = strrep(o.name, '"', '""');
        fprintf(fid, '%s,"%s",%s,%s,%s,%.2f,%s,%s,%s,%s,%s,%s,"%s"\n', ...
            o.test_id, nameClean, o.category, o.severity, o.status, ...
            o.execution_time_ms, w_exp, w_act, os_act, ts_act, i_act, ...
            reasonsStr, o.source);
    end

    csvPath = outputPath;
end
