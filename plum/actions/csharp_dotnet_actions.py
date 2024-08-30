import os
import re
import logging
import subprocess
import shlex

from glob import glob
from pathlib import Path
from plum.actions._docker_runner import DockerRunner
from plum.actions.actions import Actions
from plum.actions.csharp._sln_parser import Solution
from plum.actions.csharp.build_manager import BuildManager
from plum.actions.csharp.upgrade_manager import UpgradeManager
from plum.actions.csharp.coverage_manager import CoverageManager
from plum.utils.cobertura import get_function_coverage
from plum.utils.logger import Logger

TIMEOUT = 1000
DOCKER_TIMEOUT = 900


class CsharpDotnetActions(Actions):
    """
    Class used to represent the Maven actions that can be taken on an environment object
    in Csharp

    Attributes:
    -----------
    environment: the environment object that we are taking actions on
                Could be a repository, a directory, etc etc.

    """

    def __init__(
        self,
        environment,
        docker_image,
        docker_tag,
        docker_work_dir="/app",
        local_repository="",
    ):
        super().__init__(environment)
        self.docker_image = docker_image
        self.docker_tag = docker_tag
        self.docker_work_dir = docker_work_dir
        self.repo_full_path = Path(os.path.join(
                environment.base, environment.internal_repo_path
        )).resolve()
        if environment.repo_type.name == 'LOCAL' or environment.repo_type.name == 'TEST':
            self.repo_full_path = environment.base

        self.docker_runner = DockerRunner(docker_image, docker_tag, docker_work_dir)
        """Holds Docker configuration and runs Docker commands."""

    def clean(self):
        """
        Run 'dotnet clean' in a Docker container to clean the project, deleting build files and target folders.
        The docker command mounts a volume pointing to the repo folder into the docker working directory, and it executes the command.

        Returns:
            dict: A dictionary with the cleaning result, including status, stdout, and stderr.
        """
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} dotnet clean"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        status_result = self.parse_build(stdout)
        result = {
            "status_result": status_result,
            "stdout": stdout,
            "stderr": stderr,
        }

        return result

    def build(self):
        """
        Run 'dotnet build' in a Docker container to build the project, creating target folders and binary files.
        The docker command mounts a volume pointing to the repo folder into the docker working directory, and it executes the command.

        Returns:
            dict: A dictionary with the building result, including status, stdout, and stderr.
        """
        # TODO: The BuildManager should ideally be initialized earlier, but that would take more refactoring.
        # NOTE: The properties of the DockerRunner will be changed by the BuildManager.
        build_manager = BuildManager(
            repo_full_path=self.repo_full_path,
            docker_runner=self.docker_runner,
            timeout=DOCKER_TIMEOUT,
        )

        build_res = build_manager.build()

        result = {
            "status_result": "SUCCESS" if build_res["success"] else "FAILURE",
            "stdout": build_res["stdout"],
            "stderr": build_res["stderr"],
        }

        # DEBUG: Output successful build config
        if build_res["success"]:
            logging.debug(f"({self.repo_full_path}): {self.docker_runner.image}:{self.docker_runner.tag}")

        return result

    def upgrade(self, upgrade_to_version: str):
        if float(self.docker_runner.tag) < 6.0:
            self.docker_runner.tag = "6.0"

        upgrade_manager = UpgradeManager(
            repo_full_path=self.repo_full_path,
            docker_runner=self.docker_runner,
            upgrade_to_version=upgrade_to_version,
            timeout=DOCKER_TIMEOUT,
        )
        res = upgrade_manager.upgrade()
        result = {
            "status_result": "SUCCESS" if res["success"] else "FAILURE",
            "stdout": res["stdout"],
            "stderr": res["stderr"],
        }

        # DEBUG: Output successful build config
        if res["success"]:
            logging.debug(f"({self.repo_full_path}): {self.docker_runner.image}:{self.docker_runner.tag}")

        return result

    def run_test_suite(self, timeout=TIMEOUT):
        """
        Run 'dotnet test' in a Docker container to run the tests within the project.
        The docker command mounts a volume pointing to the repo folder into the docker working directory, and it executes the command.

        Returns:
            dict: A dictionary with the testing result, including status, stdout, stderr, and number of passed/failed/skipped tests.
        """
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} dotnet test"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=timeout
            )

        except subprocess.TimeoutExpired:
            Logger().get_logger().error(f"TimeoutExpired: Your timeout is currently {timeout}s. Increase timeout if needed")
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        test_results = self.parse_dotnet_test(stdout)
        status_result = "FAILURE"
        if "status" in test_results:
            status_result = test_results["status"]
        result = {
            "status_result": status_result,
            "test_results": test_results,
            "stdout": stdout,
            "stderr": stderr,
        }
        return result


    def run_custom_command(self, command):
        """
        Run any custom command within the Docker container.
        The docker command mounts a volume pointing to the repo folder into the docker working directory, and it executes the command.

        Returns:
            dict: A dictionary with the testing result, including status, stdout, stderr.
        """
        try:
            command = f'docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} {command}'
            output = subprocess.run(shlex.split(command), capture_output=True, timeout=TIMEOUT)

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        result = {"stdout": stdout, "stderr": stderr}
        return result

    def get_coverage(self):
        """
        Generate coverage report using dotnet test command and the coverlet package.
        """
        coverage_manager_res = CoverageManager.load(self.repo_full_path, self.docker_runner)
        if not coverage_manager_res["success"]:
            return coverage_manager_res

        coverage_manager = coverage_manager_res["manager"]
        coverlet_install_res = coverage_manager.install_coverlet()
        if not coverlet_install_res["success"]:
            return coverlet_install_res

        coverage_reports = coverage_manager.run_coverage()

        return coverage_reports

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

        # Ensure that the environment we're using has hash2function populated.
        if not hasattr(self.environment, 'hash2function'):
            _ = self.environment.get_functions()

        fn2coverage = get_function_coverage(cobertura_coverage_report, self.environment.hash2function, "csharp")

        return fn2coverage

    # ------------------- PARSING UTILITIES -------------------

    def parse_build(self, dotnet_ouptut):
        if "Build FAILED." in dotnet_ouptut:
            return "FAILURE"
        else:
            return "SUCCESS"

    def parse_dotnet_test(self, stdout):
        # Regular expression pattern to match the test results line
        pattern = r'(Failed|Passed)!\s+-\s+Failed:\s+(\d+),\s+Passed:\s+(\d+),\s+Skipped:\s+(\d+),\s+Total:\s+(\d+)'

        # Search for the pattern in the input string
        match = re.search(pattern, stdout)

        if match:
            # Extract the numbers of failed, passed, and skipped tests
            status = match.group(1)
            failed = int(match.group(2))
            passed = int(match.group(3))
            skipped = int(match.group(4))
            total = int(match.group(5))

            return {
                'status': status,
                'failed': failed,
                'passed': passed,
                'skipped': skipped,
                'total': total
            }
        else:
            # If no match is found, return None
            return None

    def get_test_projects(self):
        """
        Retrieve all test projects from the first solution found in this repo.

        Returns:
            List[CsProj]: A list of CsProj objects.
        """
        sln_files = glob(os.path.join(self.repo_full_path, '*.sln'))
        if not sln_files:
            raise FileNotFoundError("No .sln file found for test generation.")
        if len(sln_files) > 1:
            Logger().get_logger().warning(f"WARNING: Multiple .sln files found for test generation. Using first file:{list(sln_files)}")
        solution_path = os.path.join(self.repo_full_path, sln_files[0])
        solution = Solution.from_file(solution_path)
        return solution.get_test_projects()
