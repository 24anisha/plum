"""End to End Example Usage of PLUM with Python Repositories"""
import argparse
import pprint

from plum.environments.py_repo import PythonRepository
from plum.actions.py_actions import PythonActions
from plum.utils.test_report_parsers import get_pytest_test_failures, remove_fn_from_file


def method_alteration_experiment(repo_name, base, cleanup):
    """
    Example experimental pipeline for one git repo: run the tests in the repo & get a list of covered functions.
    Then, overwrite one of the functions from the repo with a "hello world" print statement, and see which tests fail.
    """

    # Initialize PythonRepository environment object
    repo = PythonRepository(base, repo_name)

    repo.setup(cleanup=cleanup)
    functions = repo.get_functions()

    # initialize instance of PythonActions class, which has functionality for interacting with the environment object
    plum = PythonActions(repo)

    # get a JSON report of the result of running the test suite on the repo
    control_test_report = plum.run_test_suite()

    # get a list of functions in the repo that are covered by the repo's tests
    covered_functions = plum.get_covered_functions()

    for fnhash, function in functions.items():
        if fnhash in covered_functions:

            # Function objects represent each of the functions in the repo, and have attributes such as the function body
            new_function = function
            new_function.body = "   print('hello world')"

            # save original file contents before writing new function to file
            file_path = repo.base / repo.internal_repo_path / function.relative_path
            original_file_contents = open(file_path).read()

            # write the function's new body to the original file and re-run the test suite to see
            # which test cases fail
            plum.write_snippet_to_file(new_function, file_path, snippet_type='function')
            test_report = plum.run_test_suite()

            failed_tests = get_pytest_test_failures(control_test_report, test_report)
            print(failed_tests.keys())

            # rewrite the original file contents
            with open(file_path, "w") as f:
                f.write(original_file_contents)


def main():

    parser = argparse.ArgumentParser(description='Process arguments for method generation experiment')
    parser.add_argument("-b", "--base", type=str, help="base path where the repo will be cloned", required=True)
    args = parser.parse_args()

    # passing a github user/repo_name to the environment class will result in the repo being cloned locally to the base path
    # in order to complete the rest of the steps in the PLUM evaluation
    repo = 'johanrosenkilde/nasty_python'
    method_alteration_experiment(repo, args.base, True)


if __name__ == '__main__':
    main()


