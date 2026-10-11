function summary = run_all_tests(configPath, outputDir)
% RUN_ALL_TESTS Primary MATLAB entry point for SimuVerify test suite execution
%
% Syntax:
%   summary = run_all_tests()
%   summary = run_all_tests(configPath, outputDir)
%
% Inputs:
%   configPath - Optional path to config/test_cases.json
%   outputDir  - Optional path to reports directory
%
% Outputs:
%   summary    - Struct with aggregate execution metrics and outcomes
%
% Example:
%   >> addpath(genpath('matlab'))
%   >> summary = run_all_tests;

    thisDir = fileparts(mfilename('fullpath'));
    projectRoot = fullfile(thisDir, '..', '..');

    if nargin < 1 || isempty(configPath)
        configPath = fullfile(projectRoot, 'config', 'test_cases.json');
    end

    if nargin < 2 || isempty(outputDir)
        outputDir = fullfile(projectRoot, 'reports');
    end

    % Ensure matlab directories are in path
    addpath(fullfile(projectRoot, 'matlab', 'config'));
    addpath(fullfile(projectRoot, 'matlab', 'sim'));
    addpath(fullfile(projectRoot, 'matlab', 'runner'));
    addpath(fullfile(projectRoot, 'matlab', 'reporting'));

    % 1. Load test suite
    fprintf('[*] Loading test suite: %s\n', configPath);
    suite = load_test_cases(configPath);

    % 2. Run tests
    runner = TestRunner();
    summary = runner.runSuite(suite);

    % 3. Export reports
    csvPath = fullfile(outputDir, 'validation_summary.csv');
    htmlPath = fullfile(outputDir, 'validation_report.html');

    export_csv(summary, csvPath);
    export_html(summary, htmlPath);

    fprintf('[+] Reports successfully generated:\n');
    fprintf('    ├── CSV Report : %s\n', csvPath);
    fprintf('    └── HTML Report: %s\n\n', htmlPath);
end
