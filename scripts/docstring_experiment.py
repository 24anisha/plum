"""Code for completing the docstring experiment in Python using the plum api"""
from plum.environments.py_repo import PythonRepository
from plum.actions.py_actions import PythonActions
from plum.utils.llms import nonchat_gpt
from multiprocessing import Process, cpu_count
from multiprocessing.dummy import Pool


def docstring_experiment(repo_name=""):
    """
    Experimental pipeline for one git repo: method generation using generated docstrings.
    """
    # set up the repo environment and state
    # repo = PythonRepository('path/to/base', 'owner/repo_name')
    repo = PythonRepository('/home/anisagarwal/data/plum_trials', 'AlbertFX91/jsonty')

    repo.setup(cleanup=True)
    functions = repo.get_functions()

    # initialize instance of class with functionality for interacting with environment object (repo)
    plum = PythonActions(repo)

    # filter on covered functions
    control_test_report = plum.run_test_suite()
    covered_functions = plum.get_covered_functions()

    # if len(control_test_report['tests'])>0:

    #     if not min([d['outcome']=='passed' for d in control_test_report['tests']]):
    #         result = "success"
    #     else:
    #         result = "test_failures"
    # else:
    #     result = "broken_suite"
    
    # with open('/home/anisagarwal/data/plum-api/results.txt', 'a') as f:
    #     f.write(f"{repo_name}, {result}\n")

    # for fnhash, function in functions.items():
    #     if fnhash in covered_functions:
    #         new_function = get_altered_function(function)
            
    #         # save original file contents before writing new function to file
    #         file_path = repo.base / repo.internal_repo_path / function.relative_path
    #         original_file_contents = open(file_path).read()
    #         plum.write_snippet_to_file(new_function, file_path, snippet_type='function')

    #         test_report = plum.run_test_suite()
    #         failed_tests = get_test_failures(control_test_report, test_report)
    #         # TODO aaron/yevhen: save failed tests in desired format

    #         with open(file_path, "w") as f:
    #             f.write(original_file_contents)


def get_test_failures(control_test_report, new_test_report):
    """
    Compare the control test report to the new test report
    :param control_test_report: the test report before the new snippet was written
    :param new_test_report: the test report after the new snippet was written
    :return: a list of tests that failed after the new snippet was written
    """

    control_dict = {}
    experiment_dict = {}
    for test in control_test_report['tests']:
        control_dict[test['nodeid']] = test['outcome']
    
    for test in new_test_report['tests']:
        experiment_dict[test['nodeid']] = test['outcome']

    failed_tests = []
    for key in control_dict:
        if key not in experiment_dict:
            failed_tests.append(key)
        elif control_dict[key] == "passed" and experiment_dict[key] == "failed":
            failed_tests.append(key)

    print(failed_tests)
    return failed_tests


def get_altered_function(function):
    """
    Helper method to take the original function, generate a new docstring, and generate a new body
    :param function: the original function
    :return: the new function with the new docstring and body 
    """
    new_function = function

    # generate the new docstring based on the function body
    docstring_prompt = f"""
<|im_start|>system
PROMPT FOR CHANGING DOCSTRING GIVEN {function.signature}, {function.body}
<|im_end|><|im_start|>assistant
"""

    generated_docstring = nonchat_gpt(docstring_prompt)

    # generate the new body based on generated docstring
    body_prompt = f"""
<|im_start|>system
PROMPT FOR CHANGING BODY GIVEN {function.signature}, {generated_docstring}
<|im_end|><|im_start|>assistant
"""

    generated_body = nonchat_gpt(body_prompt)
    new_function.docstring = generated_docstring
    new_function.body = generated_body

    return new_function


def main():
    with open('/home/anisagarwal/data/plum-api/plum/data/100_python_repos.csv', 'r') as f:
        repos = f.readlines()[1:]
    # pool = Pool(processes=cpu_count())
    # for repo in repos:
    #     try:
    #         repo = repo.strip()
    #         # pool.apply_async(docstring_experiment, args=repo)
    #         docstring_experiment(repo)
    #     except Exception as e:
    #         with open('/home/anisagarwal/data/plum-api/failed_repos.txt', 'a') as f:
    #             f.write(f"{repo}\n")
    #         print(e)
    #         continue
    docstring_experiment()
    # pool.close()
    # pool.join()

main()



