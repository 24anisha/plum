"""Code for completing the method generation experiment in Python using the plum api"""
from plum.environments.py_repo import PythonRepository
from plum.actions.py_actions import PythonActions
from plum.utils.llms import nonchat_gpt
import json
from pathlib import Path
import fileinput

def method_generation_experiment(base_path, repo_name, cleanup):
    """
    Experimental pipeline for one git repo: method generation using original docstrings.
    """
    # set up the repo environment and state
    print(repo_name)
    repo = PythonRepository(base_path, repo_name)

    repo.setup(cleanup=cleanup)
    functions = repo.get_functions()

    # initialize instance of class with functionality for interacting with environment object (repo)
    plum = PythonActions(repo)
    # filter on covered functions
    control_test_report = plum.run_test_suite()
    covered_functions = plum.get_covered_functions()

    if len(control_test_report['tests'])>0:

        if min([d['outcome']=='passed' for d in control_test_report['tests']]):
            result = "success"
        else:
            result = "test_failures"
    else:
        result = "broken_suite"

    with open(base_path / 'repo_results.txt', 'a') as f:
        f.write(f"{repo_name}, {result}\n")

    if result != "success":
        raise Exception("Test suite is broken")

    for fnhash, function in functions.items():
        if fnhash in covered_functions:

            # TODO CHANGE THIS BACK FOR OTHER EXPERIMENTS
            new_function = get_altered_function_w_file_context(function, repo)

            # new_function = get_altered_function(function)
            # save original file contents before writing new function to file
            file_path = repo.base / repo.internal_repo_path / function.relative_path
            original_file_contents = open(file_path).read()

            plum.write_snippet_to_file(new_function, file_path, snippet_type='function')

            new_file_contents = open(file_path).read()
            
            test_report = plum.run_test_suite()
            failed_tests = get_test_failures(control_test_report, test_report)

            with open(file_path, "w") as f:
                f.write(original_file_contents)
            
            # saving the data of the run
            method_dict = {
                "repo_name": repo_name,
                "fnhash": fnhash,
                "original_fn": function.function_dict,
                "new_fn": new_function.function_dict,
                "failed_tests": failed_tests,
                "success": len(failed_tests)==0
            }
            write_data_jsonl(method_dict, base_path / 'method_generation_experiment.jsonl')
            print(fnhash)


def write_data_jsonl(method_dict, writepath):
    with open(writepath, 'a', encoding='utf-8') as f:
        json.dump(method_dict, f, ensure_ascii=False)
        f.write('\n')


def get_error_dict(test_dict, run_section='call'):
    """
    Get the error dictionary for a given test
    :param test_dict: the test dictionary
    :param run_section: the section of the test dictionary to look in (setup, call or teardown)
    """
    if 'longrepr' in test_dict[run_section]:
        longrepr = test_dict[run_section]['longrepr']
    else:
        longrepr = ""
    if 'traceback' in test_dict[run_section]:
        traceback = test_dict[run_section]['traceback']
    else:
        traceback = ""

    error_dict = {
        "outcome": test_dict['outcome'],
        "longrepr": longrepr,
        "traceback": traceback
    }

    return error_dict


def get_test_failures(control_test_report, new_test_report):
    """
    Compare the control test report to the new test report
    :param control_test_report: the test report before the new snippet was written
    :param new_test_report: the test report after the new snippet was written
    :return: a list of dicts, where each dict represents a that failed after the new snippet was written
        each dict contains the following keys:
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
            test_status[section] = test[section]

        experiment_dict[test['nodeid']] = test_status

    failed_tests = []
    for key in control_dict:
        if key not in experiment_dict:
            error_dict = {"outcome": "did_not_run"}
            failed_tests.append({key: error_dict})
        elif control_dict[key] == "passed" and experiment_dict[key]['outcome'] == "failed":
            failed_tests.append({key: experiment_dict[key]})

    return failed_tests

###################################################################################################################
# Code for Experiment with File Context
###################################################################################################################
def get_file_context(function, environment):
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


def get_altered_function_w_file_context(function, environment=None):
    """
    Helper method to take the original function, generate a new docstring, and generate a new body
    Takes the focal file as context for generating the new function
    :param function: the original function
    :return: the new function with the new docstring and body 
    """
    new_function = function

    # generate the new body based on docstring and signature
    updated_file_contents = get_file_context(function, environment)
    body_prompt = f"""
<|im_start|>system
Given the following file contents and a docstring for a method that will be added to the file, complete the method. DO NOT repeat any code that has been provided. Only fill in the function.
-----------------------------------------------------------------------------------------------------
File Contents:
{updated_file_contents}

-----------------------------------------------------------------------------------------------------
Docstring for New Method:
{function.docstring}
<|im_end|><|im_start|>assistant
{function.signature}
"""
    generated_body = nonchat_gpt(body_prompt)
    new_function.body = generated_body

    return new_function
###################################################################################################################
###################################################################################################################


def get_altered_function(function):
    """
    Helper method to take the original function, generate a new docstring, and generate a new body
    :param function: the original function
    :return: the new function with the new docstring and body 
    """
    new_function = function

    # generate the new body based on docstring and signature
    body_prompt = f"""
<|im_start|>system
Complete the following python function given the docstring. DO NOT repeat any code that has been provided. Only fill in the function.
{function.docstring}
<|im_end|><|im_start|>assistant
{function.signature}
"""
    generated_body = nonchat_gpt(body_prompt)
    new_function.body = generated_body

    return new_function

def main():
    # TODO change this to the path to the plum-api directory
    base_path = "INSERT/YOUR/BASE/PATH/HERE"
    with open('/path/to/plum-api/plum/data/100_python_repos.csv', 'r') as f:
        repos = f.readlines()[1:]

    for repo in repos:
        try:
            repo = repo.strip()
            method_generation_experiment(base_path, repo, False)
        except Exception as e:
            with open(base_path / 'failed_repos.txt', 'a') as f:
                f.write(f"{repo}\n")
            print(e)


if __name__ == '__main__':
    main()


