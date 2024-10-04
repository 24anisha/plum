import sys
import pytest
import os
import json
from pathlib import Path

from plum.environments import Repository
from plum.environments.py_repo import PythonRepository
from plum.environments.cpp_repo import CppRepository
from plum.environments.csharp_repo import CsharpRepository
from plum.environments.java_repo import JavaRepository
from plum.harnesslib.languages import Language

from plum.actions import Actions
from plum.actions.py_actions import PythonActions

# Get the absolute path of the current script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

# Get the absolute path of the '.data' folder
DATA_DIRECTORY = os.fspath(os.path.join(script_dir, '.data'))
@pytest.mark.parametrize(
    "repo_name",
    [
        ("johanrosenkilde/nasty_python"),
        # ("keras-team/keras"),
        # ("fxsjy/jieba"),
        # ("pallets/flask"), 
        # ("bregman-arie/devops-exercises"),
        # ("soimort/you-get"),
        # ("scrapy/scrapy"),
    ],
)

def test_setup_python(repo_name):
    def remove_key(data, key):
        """Recursively remove the specified key from nested dictionaries"""
        if isinstance(data, dict):
            data.pop(key, None)
            for value in data.values():
                remove_key(value, key)
        elif isinstance(data, list):
            for item in data:
                remove_key(item, key)

    def load_report_without_duration(report_file):
        """returns the report json with any duration keys"""
        with open(report_file, 'r') as f:
            report_dict = json.load(report_file)
        remove_key(report_dict, "duration")
        return report_dict
    
    print("Starting test for repo:", repo_name)

    # Test PythonRepository setup
    try:
        pythonRepo = PythonRepository(DATA_DIRECTORY, repo_name)
        pythonRepo.setup(cleanup=False)
        pythonFunctions = pythonRepo.get_functions()
        print(f"PythonRepository setup complete for {repo_name}")
    except Exception as e:
        pytest.fail(f"PythonRepository setup failed with exception: {e} for repo {repo_name}")
    
    # Test generic Repository setup
    try:
        repo = Repository("python", DATA_DIRECTORY, repo_name)
        repo.setup(cleanup=False)
        functions = repo.get_functions()
        print(f"Repository setup complete for {repo_name}")
    except Exception as e:
        pytest.fail(f"Repository setup failed with exception: {e} for repo {repo_name}")

    # Compare the PythonRepository and Repository objects
    assert isinstance(pythonRepo, PythonRepository) and isinstance(repo, PythonRepository), f"Repository function and PythonRepository differ for {repo_name}"
    assert len(pythonFunctions) == len(functions), "Repository function and PythonRepository"

    # base case
    python_plum = PythonActions(pythonRepo)
    python_control_test_report = python_plum.run_test_suite()
    print("control_test_report with PythonActions", python_control_test_report)


    # try refactored Repo with refactored Action
    plum = Actions("python", repo)
    control_test_report = plum.run_test_suite()
    print("control_test_report with Action", control_test_report)
    assert control_test_report is not None
    if "success" in control_test_report and control_test_report["success"] is False:
        assert False, f"refactored Action test suite failed for {repo_name}, with report: {control_test_report}"
    if "summary" in control_test_report and "total" in control_test_report["summary"]:
        assert control_test_report["summary"]["total"] > 0, f"no tests were found for {repo_name}"

    assert isinstance(python_plum, PythonActions) and isinstance(plum, PythonActions), f"Actions function and PythonActions differ for {repo_name}"

    remove_key(python_control_test_report, "duration")
    remove_key(control_test_report, "duration")
    remove_key(python_control_test_report, "created")
    remove_key(control_test_report, "created")


    assert python_control_test_report == control_test_report, "Action function and PythonAction class return different test reports"


