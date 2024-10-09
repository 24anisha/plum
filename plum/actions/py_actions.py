import os
import logging
import json
import subprocess
from pathlib import Path
import shlex
from tree_sitter import Language as L, Parser
import fileinput

from plum.utils import fix_indentation, get_pytest_test_failures, remove_fn_from_file, fnhash
from plum.harnesslib.languages import Language
import plum.harnesslib.tasks as tasks

from plum.environments.repository import Repository
from plum.actions.actions import Actions
from plum.utils.logger import Logger


class PythonActions(Actions):
    """
    Class used to represent the actions that can be taken on an environment object
    in Python

    Attributes:
    -----------
    environment: the environment object that we are taking actions on
                Could be a repository, a directory, etc etc.

    """

    def __init__(self, environment):
        super().__init__(environment)


    def run_test_suite(self, timeout=30):
        """
        Run the existing test suite of the environment
        :returns: JSON report of which tests passed and failed
        """

        try:
            command = f'{os.fspath(self.environment.interpreter_path)} -m pytest --json-report'
            output = subprocess.run(shlex.split(command), cwd=self.environment.repo_root, capture_output=True, timeout=timeout)

        except subprocess.TimeoutExpired:
            Logger().get_logger().error(f"TimeoutExpired: Your timeout is currently {timeout}s. Increase timeout if needed")
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result


        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        Logger().get_logger().info(stdout)
        Logger().get_logger().debug(stderr)

        with open(self.environment.repo_root / '.report.json', 'r') as f:
            pytest_report = json.load(f)
        return pytest_report


    def get_coverage(self):
        """
        Get coverage report for repo (with all files + covered lines)
        :returns: JSON report of covered lines in each file
        """
        try:
            if not os.path.exists('coverage.json'):

                # run 2 subprocess commands to get coverage json
                # map tests back to functions by running pytest for each individual test & getting which lines are covered                
                command = f"{os.fspath(self.environment.interpreter_path)} -m coverage run {self.environment.repo_root}-venv/bin/pytest"
                output = subprocess.run(shlex.split(command), cwd=self.environment.repo_root, capture_output=True)

                command = f"{os.fspath(self.environment.interpreter_path)} -m coverage json"
                output = subprocess.run(shlex.split(command), cwd=self.environment.repo_root, capture_output=True)

            with open(self.environment.repo_root / 'coverage.json', 'r') as f:
                coverage_report = json.load(f)
            return coverage_report

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result


    def get_covered_functions(self):
        """
        Get list of focal functions with coverage
        :returns: dictionary mapping function hash to list of covered lines
        """
        try:
            fn2coverage = {}
            Logger().get_logger().info("getting coverage report...")
            coverage_report = self.get_coverage()
            # if it did not succeed in getting the coverage report, return the unsuccessful coverage dictionary
            if coverage_report.get("success", "") == False:
                return coverage_report

            for fnhash, function in self.environment.hash2function.items():
                # if the focal file is in the coverage report, check if the focal function has covered lines
                if function.relative_path in coverage_report['files'].keys():
                    file_executed_lines = coverage_report['files'][function.relative_path]['executed_lines']
                    covered_lines = [element for element in file_executed_lines if function.start_line + 1 <= element <= function.end_line + 1]
                    # if covered_lines is only 1, then only the signature is being run, not the test itself
                    if len(covered_lines) > 1:
                        fn2coverage[fnhash] = covered_lines

            return fn2coverage

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result
    

    def map_tests_to_functions(self, control_test_report):
        """
        Map tests to the functions they test in the focal file
        NOTE: this is a time intensive call
        :param control_test_report: the test report for the repo before any methods have been removed
        :returns: dictionary mapping function hash to list of tests that cover it
        """

        fn2tests = {}

        for fnhash, function in self.environment.hash2function.items():

            # save original file contents
            file_path = self.environment.base / self.environment.internal_repo_path / function.relative_path
            original_file_contents = open(file_path).read()

            # delete function from focal file
            updated_file_contents = remove_fn_from_file(function, self.environment)
            with open(file_path, "w") as f:
                f.write(updated_file_contents)

            # run full test suite
            test_report = self.run_test_suite()

            # map failing tests to focal function
            failing_tests = get_pytest_test_failures(control_test_report, test_report)
            
            fn2tests[fnhash] = failing_tests.keys()

            # rewrite original file contents
            with open(file_path, "w") as f:
                f.write(original_file_contents)
        
        # delete the json report file (if it still exists)
        os.remove(self.environment.base / self.environment.internal_repo_path / '.report.json')

        return fn2tests
        # TODO update to this algorithm once I find a way to run coverage for specific tests
        # for nodeid in test report:
        #   get the pytest coverage json report for running that test
        #   get the list of covered lines after running that test
        #   for each function in fn2coverage, see if the covered lines are in the list
        #   if they are, add the function to the list of functions that are covered by the test
        # issue: how to get coverage for each individual test? requires unittest?
        # run coverage * # tests


    def write_snippet_to_file(self, snippet, file_path, snippet_type='function'):
        """
        Write a snippet to a file
        params: 
        :snippet_text: the content to be written into the file
        :path: the path to the file
        :snippet: the type of snippet to be written (function, docstring, lines of code, etc)
        """
        if snippet_type == 'function':
            function = ""
            # if snippet is a function, we need to build and write the function
            if snippet.docstring:
                function += f'"""\n{snippet.docstring}\n"""'
            if snippet.signature:
                function += f"\n{snippet.signature}\n"
            if snippet.body:
                function += f"\n{snippet.body}\n"

            # TODO add decorators/attributes 
        with fileinput.FileInput(file_path, inplace=True) as file:
            for line_number, line in enumerate(file, start=0):
                # if it's the code to be deleted, skip it
                if line_number >= snippet.start_line and line_number <= snippet.end_line:
                    continue
                elif line_number == snippet.end_line + 1:
                    print.info(function, end='\n')
                else:
                    print.info(line, end='')
        # use autopep8 to rewrite/fix the contents to have the correct indentation
        # TODO could be the cause of the error
        fixed_contents = fix_indentation(open(file_path).read())
        with open(file_path, 'w') as f:
            f.write(fixed_contents)

    def run_generated_test(self, generated_test: str, test_file: Path, overwrite=True) -> dict:
        """
        Run a generated test and return the results.
        :param generated_test: string output from the model of a generated test suite/test case
        :param test_file: the path to the file where the generated test should be saved
        :param overwrite: whether to overwrite or append the generated_test string if the test_file path already exists
        :return: dict containing the results of the test execution
        """
        saved_file = self.save_generated_test(generated_test, test_file, overwrite)
        return self.execute_test(saved_file)
    
    def save_generated_test(self, generated_test: str, test_file: Path = None, overwrite=True) -> Path:
        """
        Save the generated test at the correct location, with the correct formatting.

        :param generated_test: string output from the model of a generated test suite/test case
        :param test_file: the path to the file where the generated test should be saved
        :param overwrite: whether to overwrite or append the generated_test string if the test_file path already exists
        :return: Path to the saved test file
        """
        if test_file is None:
            # Generate a default test file name if not provided
            test_file = self.cwd / "generated_test.py"
        mode = 'w' if overwrite else 'a'
        with open(test_file, mode) as f:
            f.write(generated_test)
        return test_file

    def execute_test(self, test_file, timeout=2):
        """
        Given a path to a file with a test in it, 
        evaluate the test in the given repo context and return
        a single output in the form
        {path: path_to_generated_test, 
            success: True/False of test passing
            stdout: stdout of running npm test
            stderr: stderror of running npm test
        }
        """

        try:
            repo_path = self.environment.base / self.environment.internal_repo_path
            output = subprocess.run([f"{repo_path}-venv/bin/pytest", test_file], capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            result = {"path": str(test_file), "success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        if "passed" in stdout:
            result = {"path": str(test_file), "success": True, "stdout": stdout, "stderr": stderr}
        else:
            result = {"path": str(test_file), "success": False, "stdout": stdout, "stderr": stderr}

        return result
