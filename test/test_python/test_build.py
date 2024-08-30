import sys
import pytest
import os
from pathlib import Path


from plum.actions.py_actions import PythonActions
from plum.environments.py_repo import PythonRepository

# NOTE: All tests do not pass at this point in time


# Get the absolute path of the current script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

# Get the absolute path of the '.data' folder
DATA_DIRECTORY = os.fspath(os.path.join(script_dir, '.data'))

# @pytest.mark.skip(reason="This is a long running test, only use if you need to run a fresh setup.")
@pytest.mark.parametrize(
    "repo_name",
    [
        ("keras-team/keras"),
        ("fxsjy/jieba"),
        ("pallets/flask"),
        ("bregman-arie/devops-exercises"),
        ("soimort/you-get"),
        ("scrapy/scrapy"),
    ],
)
def test_repo_clean_setup(repo_name):
    print("Starting test for repo_name:", repo_name)
    try:
        repo = PythonRepository(
            DATA_DIRECTORY,
            repo_name,
        )
        print("starting repo setup")
        repo.setup(cleanup=True)
        print("finishing repo setup...")
        assert True, f"setup complete for {repo_name}"
    except Exception as e:
        assert False, f"test failed with exception {e} for repo {repo_name}"

    function_list = repo.get_functions()
    print("function_list length", len(function_list))
    assert len(function_list) > 0


@pytest.mark.parametrize(
    "repo_name, expected_function_count",
    [
        ("keras-team/keras", 5190),
        ("fxsjy/jieba", 107),
        ("pallets/flask", 354),
        ("bregman-arie/devops-exercises", 24),
        ("soimort/you-get", 609),
        ("scrapy/scrapy", 1515),
    ],
)
def test_repo_function_collect(repo_name, expected_function_count):
    print("Starting test for repo_name:", repo_name)
    try:
        repo = PythonRepository(
            DATA_DIRECTORY,
            repo_name,
        )
        print("cleanup set to false.")
        repo.setup(cleanup=False)
        assert True, f"setup complete for {repo_name}"
    except Exception as e:
        assert False, f"test failed with exception {e} for repo {repo_name}"

    print("getting functions from the given repo")
    function_list = repo.get_functions()
    print(f"expected to find {expected_function_count} and found {len(function_list)}")
    if len(function_list) != expected_function_count:
        print("function list has changed since this test was last updated, might be worth updating.")
    assert len(function_list) > 0, f"function count was 0 for {repo_name}"
    assert len(function_list) >= expected_function_count, f"function count was less than expected for {repo_name}"


@pytest.mark.parametrize(
    "repo_name",
    [
        ("keras-team/keras"),
        ("fxsjy/jieba"),
        ("pallets/flask"), 
        ("bregman-arie/devops-exercises"),
        ("soimort/you-get"),
        ("scrapy/scrapy"),
    ],
)
def test_repo_test_run(repo_name):
    print("Starting test for repo_name:", repo_name)
    try:
        repo = PythonRepository(
            DATA_DIRECTORY,
            repo_name,
        )
        print("cleanup set to false.")
        repo.setup(cleanup=False)
        assert True, f"setup complete for {repo_name}"
    except Exception as e:
        assert False, f"test failed with exception {e} for repo {repo_name}"

    plum = PythonActions(repo)
    control_test_report = plum.run_test_suite()
    print("control_test_report", control_test_report)
    assert control_test_report is not None
    if "success" in control_test_report and control_test_report["success"] is False:
        assert False, f"test suite failed for {repo_name}, with report: {control_test_report}"
    if "summary" in control_test_report and "total" in control_test_report["summary"]:
        assert control_test_report["summary"]["total"] > 0, f"no tests were found for {repo_name}"


@pytest.mark.parametrize(
    "repo_name,",
    [
        ("fxsjy/jieba"),
        ("keras-team/keras"),
        ("pallets/flask"), 
        ("bregman-arie/devops-exercises"),
        ("soimort/you-get"),
        ("scrapy/scrapy"),
    ],
)
def test_repo_coverage(repo_name):
    print("Starting test for repo_name:", repo_name)
    try:
        repo = PythonRepository(
            DATA_DIRECTORY,
            repo_name,
        )
        print("cleanup set to false.")
        repo.setup(cleanup=False)
        assert True, f"setup complete for {repo_name}"
    except Exception as e:
        assert False, f"test failed with exception {e} for repo {repo_name}"

    plum = PythonActions(repo)
    covered_functions = plum.get_covered_functions()
    print(covered_functions)
    if "success" in covered_functions and covered_functions["success"] is False:
        assert False, f"test suite failed for {repo_name}, with output: {covered_functions}"


@pytest.mark.parametrize(
    "repo_name,cleanup",
    [
        ("fxsjy/jieba", False),
    ],
)
def test_full_process(repo_name, cleanup):
    """
    This test runs the full process for a given repo from setup to coverage report.
    repo_name: the name of the repo to test
    cleanup: whether to cleanup the repo after the test (for the repo.setup function)
    test passes if setup, test run and coverage run without error and the coverage report is generated with a successful status.
    """
    try:
        repo = PythonRepository(
            DATA_DIRECTORY,
            repo_name,
        )
        print(f"cleanup set to {cleanup}.")
        repo.setup(cleanup=cleanup)
        assert True, f"[test_full_process]: setup complete for {repo_name}"
    except Exception as e:
        assert False, f"test failed with exception {e} for repo {repo_name}"

    print("getting functions from the given repo")
    function_list = repo.get_functions()
    print(f"[test_full_process]: Number of functions found: {len(function_list)}")

    plum = PythonActions(repo)
    print("running test suite")
    control_test_report = plum.run_test_suite()
    print(f"[test_full_process]: control_test_report: {control_test_report}")

    print("getting coverage report")
    covered_functions = plum.get_covered_functions()
    print(f"[test_full_process]: covered_functions: {covered_functions}")
    if "success" in covered_functions and covered_functions["success"] is False:
        assert False, f"test suite failed for {repo_name}, with output: {covered_functions}"