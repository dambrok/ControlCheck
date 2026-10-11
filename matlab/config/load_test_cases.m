function suite = load_test_cases(filePath)
% LOAD_TEST_CASES Reads and parses JSON test suite configuration.
%
% Syntax:
%   suite = load_test_cases(filePath)
%
% Inputs:
%   filePath - String or char array specifying path to test_cases.json
%
% Outputs:
%   suite    - Struct containing parsed test suite metadata and test_cases
%
% Notes:
%   Uses built-in jsondecode (requires MATLAB R2016b or newer).
%   No proprietary toolboxes required.

    if nargin < 1 || isempty(filePath)
        % Default to standard config location relative to project root
        thisDir = fileparts(mfilename('fullpath'));
        filePath = fullfile(thisDir, '..', '..', 'config', 'test_cases.json');
    end

    if ~isfile(filePath)
        error('SimuVerify:ConfigNotFound', 'Configuration file not found: %s', filePath);
    end

    fid = fopen(filePath, 'r', 'n', 'UTF-8');
    if fid == -1
        error('SimuVerify:FileOpenError', 'Unable to open file: %s', filePath);
    end
    cleaner = onCleanup(@() fclose(fid));

    rawText = fread(fid, '*char')';
    suite = jsondecode(rawText);

    % Validate minimal structure
    if ~isfield(suite, 'test_cases')
        error('SimuVerify:InvalidSchema', 'JSON missing required field "test_cases"');
    end
end
