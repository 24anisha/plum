import io
import os
import re
import logging
import json
import subprocess
import requests
import zipfile
from pathlib import Path
import shlex
from tree_sitter import Language as L, Parser
import fileinput

from plum.utils import fix_indentation, fnhash
from plum.harnesslib.languages import Language
import plum.harnesslib.tasks as tasks

from plum.environments.repository import Repository
from plum.actions.actions import Actions
from plum.utils.logger import Logger

TIMEOUT = 1000
DOCKER_TIMEOUT = 900


class CppActions(Actions):
    """
    Class used to represent the Maven actions that can be taken on an environment object
    in Cpp

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
        docker_work_dir="/data",
        repo_name="",
        local_repository="",
    ):
        super().__init__(environment)
        self.docker_image = docker_image
        self.docker_tag = docker_tag
        self.docker_work_dir = docker_work_dir
        self.repo_full_path = os.path.join(
                environment.base, environment.internal_repo_path
        )
        self.repo_name = repo_name
        if environment.repo_type.name == 'LOCAL' or environment.repo_type.name == 'TEST':
            self.repo_full_path = environment.base


    def init_docker(self, dockerfile):
        try:
            command = f"docker build -t cpp -f {dockerfile} ."
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        result = {
            "stdout": stdout,
            "stderr": stderr,
        }

        return result

    
    def create_executable_script(self, script_content, script_name):
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} /bin/bash -c 'echo {script_content} > {script_name} && chmod +x {script_name}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        result = {
            "stdout": stdout,
            "stderr": stderr,
        }

        return result


    def build(self):
        """
        Run 'build.sh' in a Docker container to build the project, creating target folders and binary files.
        The docker command mounts a volume pointing to the repo folder into the docker working directory, and it executes the command.

        Returns:
            dict: A dictionary with the building result, including status, stdout, and stderr.
        """
        try:
            script_path = os.path.join(os.path.join("/scripts", self.repo_name),"build.sh")
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} /bin/bash -c {script_path}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        status_result = self.parse_build(stdout, stderr)
        result = {
            "status_result": status_result,
            "stdout": stdout,
            "stderr": stderr,
        }

        return result


    def run_test_suite(self, timeout=TIMEOUT):
        """
        Run 'test.sh' in a Docker container to run the tests within the project.
        The docker command mounts a volume pointing to the repo folder into the docker working directory, and it executes the command.

        Returns:
            dict: A dictionary with the testing result, including status, stdout, stderr, and number of passed/failed/skipped tests.
        """
        try:
            script_path = os.path.join(os.path.join("/scripts", self.repo_name),"test.sh")
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} /bin/bash -c {script_path}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=timeout
            )

        except subprocess.TimeoutExpired:
            Logger().get_logger().error(f"TimeoutExpired: Your timeout is currently {timeout}s. Increase timeout if needed")
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        test_results = self.parse_test(stdout)
        result = {
            "status_result": test_results,
            "test_results": test_results,
            "stdout": stdout,
            "stderr": stderr,
        }
        return result


    def get_coverage(self):
        raise NotImplementedError("Coverage is not yet implemented for C++")
    

    def clean(self, build_folder):
        """
        Removes build folders in a Docker container to clean the project, deleting build files and target folders.
        The docker command mounts a volume pointing to the repo folder into the docker working directory, and it executes the command.

        Returns:
            dict: A dictionary with the cleaning result, including status, stdout, and stderr.
        """
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} sh -c 'rm -rf {build_folder}'"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
            return result

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        result = {
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


    # ------------------- PARSING UTILITIES -------------------

    def parse_build(self, stdout, stderr):
        if " Error " in stdout or " Error " in stderr:
            return "FAILURE"
        else:
            return "SUCCESS"
        
    def parse_test(self, stdout, stderr):
        if "FAILED" in stdout or " Error " in stdout or "FAILED" in stderr or " Error " in stderr:
            return "FAILURE"
        else:
            return "SUCCESS"
   
