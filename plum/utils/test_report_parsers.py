"""Helper functions for running and parsing python and javascript test suites"""


def remove_fn_from_file(function, environment):
    """
    Takes a function and removes it from the original file contents that
    the function is from
    :param function: the function to remove
    """
    file_path = environment.base / environment.internal_repo_path / function.relative_path
    file_contents = ""
    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=0):
            # if it's the code to be deleted, skip it
            if line_number >= function.start_line and line_number <= function.end_line:
                continue
            else:
                file_contents += line
    return file_contents


def get_pytest_test_failures(control_test_report, new_test_report):
    """
    PYTHON TEST FRAMEWORK REPORT COMPARISON
    Compare the control test report to a new test report
    :param control_test_report: the test report before the new snippet was written
    :param new_test_report: the test report after the new snippet was written
    :return: a dict, where each key:value pair represents a test that failed after the new snippet was written
        each key is a pytest node id, and each value is a dict that contains the following keys:
            outcome: passed or failed
            setup: dict of the setup status
            call: dict of the call status
            teardown: dict of the teardown status
    """

    control_dict = {}
    experiment_dict = {}
    for test in control_test_report['tests']:
        control_dict[test['nodeid']] = test['outcome']

    for test in new_test_report['tests']:
        test_status = {'outcome': test['outcome']}
        for section in ['setup', 'call', 'teardown']:
            if section in test:
                test_status[section] = test[section]

        experiment_dict[test['nodeid']] = test_status

    failed_tests = {}
    for key in control_dict:
        if key not in experiment_dict:
            error_dict = {"outcome": "did_not_run"}
            failed_tests[key] = error_dict
        elif control_dict[key] == "passed" and experiment_dict[key]['outcome'] == "failed":
            failed_tests[key] = experiment_dict[key]

    return failed_tests


def get_js_test_failures(control_test_report, new_test_report, test_library):
    if test_library == "mocha":
        return get_mocha_test_failures(control_test_report, new_test_report)
    elif test_library == "jest":
        return get_jest_test_failures(control_test_report, new_test_report)
    else:
        raise Exception("Unsupported test library")


def parse_jest_json_report(report):
    """
    Parse a jest json report into a dict
    :param report: the jest json report
    :return: a dict of the report
    """
    report_dict = {}
    for test_file in report['testResults']:
        filepath = test_file['name']
        for test in test_file['assertionResults']:
            test_id = filepath + "::" + test['fullName']
            test_status = {
                "outcome": test['status'],
                "failureMessages": test['failureMessages']
            }
            report_dict[test_id] = test_status
    
    return report_dict


def parse_mocha_json_report(report):
    """
    Parse a mocha json report into a dict
    :param report: the mocha json report
    :return: a dict of the report
    """

    report_dict = {}
    for status in ['passes', 'failures']:
        test_list = report[status]
        for test_dict in test_list:

            test_id = test_dict['file'] + "::" + test_dict['fullTitle']
            test_status = {
                "outcome": 'passed' if status == 'passes' else 'failed',
                "failureMessages": test_dict['err']
            }
            report_dict[test_id] = test_status
    
    return report_dict


def get_jest_test_failures(control_test_report, new_test_report):
    """
    JAVASCRIPT TEST FRAMEWORK REPORT COMPARISON
    Compare the control test report to a new test report
    :param control_test_report: the test report before the new snippet was written
    :param new_test_report: the test report after the new snippet was written
    :return: a dict, where each key:value pair represents a test that failed after the new snippet was written
        each key is a combination the test filepath and describe/test strings,
        and each value is a dict that contains the following keys:
            outcome: passed or failed
            failureMessages: list of failure messages (empty if the test passed)
    """

    # control_dict = {}
    # experiment_dict = {}
    # for report, report_dict in [(control_test_report, control_dict), (new_test_report, experiment_dict)]:
    #     for test_file in report['testResults']:
    #         filepath = test_file['name']
    #         for test in test_file['assertionResults']:
    #             test_id = filepath + "::" + test['fullName']
    #             test_status = {
    #                 "outcome": test['status'],
    #                 "failureMessages": test['failureMessages']
    #             }
    #             report_dict[test_id] = test_status
    control_dict = parse_jest_json_report(control_test_report)
    experiment_dict = parse_jest_json_report(new_test_report)

    failed_tests = {}
    for key in control_dict:
        if key not in experiment_dict:
            error_dict = {"outcome": "did_not_run"}
            failed_tests[key] = error_dict
        elif control_dict[key]['outcome'] == "passed" and experiment_dict[key]['outcome'] == "failed":
            failed_tests[key] = experiment_dict[key]

    return failed_tests


def get_mocha_test_failures(control_test_report, new_test_report):
    """
    JAVASCRIPT TEST FRAMEWORK REPORT COMPARISON
    Compare the control test report to a new test report
    :param control_test_report: the test report before the new snippet was written
    :param new_test_report: the test report after the new snippet was written
    :return: a dict, where each key:value pair represents a test that failed after the new snippet was written
        each key is a combination the test filepath and describe/it strings,
        and each value is a dict that contains the following keys:
            outcome: passed or failed
            failureMessages: failure message dict (empty if the test passed)
    """

    # control_dict = {}
    # experiment_dict = {}
    # for report, report_dict in [(control_test_report, control_dict), (new_test_report, experiment_dict)]:
    #     for status in ['passes', 'failures']:
    #         test_list = report[status]
    #         for test_dict in test_list:

    #             test_id = test_dict['file'] + "::" + test_dict['fullTitle']
    #             test_status = {
    #                 "outcome": 'passed' if status == 'passes' else 'failed',
    #                 "failureMessages": test_dict['err']
    #             }
    #             report_dict[test_id] = test_status

    control_dict = parse_mocha_json_report(control_test_report)
    experiment_dict = parse_mocha_json_report(new_test_report)
    failed_tests = {}

    for key in control_dict:
        if key not in experiment_dict:
            error_dict = {"outcome": "did_not_run"}
            failed_tests[key] = error_dict
        elif control_dict[key]['outcome'] == "passed" and experiment_dict[key]['outcome'] == "failed":
            failed_tests[key] = experiment_dict[key]

    return failed_tests
