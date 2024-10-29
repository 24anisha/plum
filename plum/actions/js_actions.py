import os
import pdb
import logging
import json
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
import shlex
from plum.harnesslib.languages import Language
import plum.harnesslib.tasks as tasks

from plum.environments.repository import Repository
from plum.actions.actions import Actions
from plum.utils.cobertura import get_function_coverage, parse_xml_as_dict
from plum.utils.logger import Logger
from plum.utils.helpers import temporary_file_content_change


class JavascriptActions(Actions):
    """
    Class used to represent the actions that can be taken on an environment object
    in Javascript

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

        TODO downstream: get javascript working for non-mocha or jest repos
        """

        try:

            if self.environment.test_library == 'mocha':

                test_command = 'mocha --reporter mocha-json-output-reporter'
                test_report = 'test-report.json'
            elif self.environment.test_library == 'jest':
                # TODO fix this
                test_command = 'jest --json --outputFile=test-report.json'
                test_report = 'test-report.json'
            # elif self.environment.test_library == 'tap':
            #     test_command = ''
            else:
                raise Exception("Unsupported test library")

            self.environment.overwrite_package_json(command=test_command, old_pkg_path='package_run_test_suite.json')
            path = self.environment.base / self.environment.internal_repo_path

            command = f'npm test'
            output = subprocess.run(shlex.split(command), cwd=path, capture_output=True, timeout=timeout)
            self.environment.rewrite_package_json(old_pkg_path='package_run_test_suite.json')

        except subprocess.TimeoutExpired:
            Logger().get_logger().error(f"TimeoutExpired: Your timeout is currently {timeout}s. Increase timeout if needed")
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        # stdout = output.stdout.decode("utf-8")
        # stderr = output.stderr.decode("utf-8")
        if os.path.exists(path / test_report):
            with open(path / test_report, 'r') as f:
                test_report = json.load(f)
        else:
            raise Exception("No test report generated")

        return test_report


    def get_coverage(self):
        """
        Get coverage report for repo (with all files + covered lines)
        :returns: JSON report of covered lines in each file
        """
        # save the original (already edited) contents of the package.json file
        # add the coverage command + json report save
        # run npm test
        # change the package.json file back to the original contents
        # return the JSON report
        if self.environment.test_library == 'mocha':
            coverage_command = 'nyc --reporter=cobertura mocha'

        elif self.environment.test_library == 'jest':
            coverage_command = 'jest --coverage --coverageReporters=cobertura'
        else:
            raise Exception("Unsupported test library")

        try:
            self.environment.overwrite_package_json(command=coverage_command, old_pkg_path='package_run_coverage.json')
            path = self.environment.base / self.environment.internal_repo_path
            command = f'npm test'
            output = subprocess.run(shlex.split(command), cwd=path, capture_output=True, timeout=100)

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            raise Exception("Timeout")

        # stdout = output.stdout.decode("utf-8")
        # stderr = output.stderr.decode("utf-8")
        expected_path = path / 'coverage/cobertura-coverage.xml'
        if os.path.exists(expected_path):
            coverage_report = parse_xml_as_dict(expected_path)
        else:
            raise Exception("No coverage report generated")

        json_data = json.dumps(coverage_report, indent=4)

        # Save the JSON data to a file
        with open(path / 'coverage/json-coverage.json', 'w') as json_file:
            json_file.write(json_data)

        self.environment.rewrite_package_json(old_pkg_path='package_run_coverage.json')

        return coverage_report


    def get_covered_functions(self, cobertura_coverage_report: dict = None):
        """
        Get list of focal functions with coverage
        :cobertura_coverage_report: the coverage report in cobertura format. Will execute coverage if not provided.

        :returns: dictionary mapping function hash to list of covered lines
        """
        if cobertura_coverage_report is None:
            Logger().get_logger().info("getting coverage report...")
            try:
                cobertura_coverage_report = self.get_coverage()
            except subprocess.TimeoutExpired:
                result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
                return result

            # if it did not succeed in getting the coverage report, return the unsuccessful coverage dictionary
            if cobertura_coverage_report.get("success", "") == False:
                return cobertura_coverage_report

        fn2coverage = get_function_coverage(cobertura_coverage_report, self.environment.hash2function, "javascript")

        return fn2coverage

    def run_generated_test(self, generated_test: str, test_file: Path, overwrite=True, timeout : int = 5) -> dict:
        """
        Run a generated test and return the results.

        :param generated_test: string output from the model of a generated test suite/test case
        :param test_file: the path to the file where the generated test should be saved
        :param overwrite: whether to overwrite or append the generated_test string if the test_file path already exists
        :param timeout: the timeout for the test execution
        :return: dict containing the results of the test execution
        """
        saved_file = self.save_generated_test(generated_test, test_file, overwrite)
        return self.execute_test(saved_file, timeout)

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
            test_file = self.cwd / "generated_test.js"

        if self.environment.test_library == "mocha":
            return test_file
        elif self.environment.test_library == "jest":
            new_test_file = test_file.with_name(f"{test_file.stem}.test{test_file.suffix}")
            mode = 'w' if overwrite else 'a'
            with open(new_test_file, mode) as f:
                f.write(generated_test)
            return new_test_file
    
    def execute_test(self, test_file: Path, timeout: int) -> dict:
        """
        Given the path to the generated test, run it and return the results.

        :param test_file: Path to the test file to be executed
        :param timeout: the timeout for the test execution
        :return: dict containing the results of the test execution
        """
        if self.environment.test_library == "mocha":
            with temporary_file_content_change(test_file, self.generated_test, mode='a'):
                return self.run_npm_test(test_file, test_library="mocha", timeout=timeout)
        elif self.environment.test_library == "jest":
            return self.run_npm_test(test_file, test_library="jest", timeout=timeout)

    def run_npm_test(self, relative_path, test_library="jest", timeout=5):
        """
        Runs npm test on a file at relative_path and get the results
        Used when appending a generated test to a focal file to see whether the test passes or fails
        NOTE only works on Mocha or Jest generated tests
        :param relative_path: the relative path of the file to run npm test on
        :param timeout: the timeout for the test execution
        """

        path = Path(self.environment.base) / self.environment.internal_repo_path
        output = subprocess.run(['npm', 'test', relative_path], cwd=path, timeout=timeout, capture_output=True)
        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        result = {
            "stdout": stdout,
            "stderr": stderr,
        }

        if test_library == "mocha":
            if "passing" in stdout and "failing" not in stdout and "0 passing" not in stdout and stderr == "":
                result['success'] = True
            else:
                result['success'] = False

        elif test_library == "jest":
            if "1 passed, 1 total" in stderr and "failed" not in stderr:
                result['success'] = True
            else:
                result['success'] = False

        return result