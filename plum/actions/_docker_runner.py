import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union

from plum.configuration.detailed_configuration_model import EnvironmentConfig

class DockerRunner:
    def __init__(self, image: str, tag: str, mount_dir: str="/app"):
        self.image = image
        """Docker image to use."""
        self.tag = tag
        """Docker tag to use."""
        self.mount_dir = DockerRunner.sterilize_path(mount_dir)
        """Directory inside the Docker container where the repo will be mounted."""

    def run(
            self,
            command: str,
            repo_path: str,
            relative_work_dir: Optional[str] = None,
            timeout=60
        ) -> Tuple[int, str, str]:
        """
        Run a command inside a Docker container.

        Args:
            command: Command to run inside the Docker container.
            repo_path: Full path to the repo.
            relative_work_dir: Specific directory inside the repo to run the command in. Defaults to the root of the repo.
            timeout: Time in seconds before the command times out.

        Returns:
            Tuple of (return code, stdout, stderr)
        """
        docker_portion = self._get_docker_command(repo_path, relative_work_dir)
        full_command = docker_portion + " " + command
        return self._run_command(full_command, timeout)

    def run_multi_command(
            self,
            commands: list[str],
            repo_path: str,
            relative_work_dir: Optional[str] = None,
            timeout=60
        ) -> Tuple[int, str, str]:
        """
        Run multiple commands inside a Docker container.

        Args:
            commands: List of commands to run inside the Docker container.
            repo_path: Full path to the repo.
            relative_work_dir: Specific directory inside the repo to run the command in. Defaults to the root of the repo.
            timeout: Time in seconds before the command times out.

        Returns:
            Tuple of (return code, stdout, stderr)
        """
        docker_portion = self._get_docker_command(repo_path, relative_work_dir)
        shell_commands = f'sh -c "{" && ".join(commands)}"'
        full_command = docker_portion + " " + shell_commands

        return self._run_command(full_command, timeout)

    def get_config(self) -> dict:
        """Get the Docker configuration."""
        return {
            "type": "docker",
            "image": self.image,
            "tag": self.tag,
            "work_dir": self.mount_dir,
        }

    @staticmethod
    def sterilize_path(path: Union[Path, str]) -> str:
        """Sterilize backslashes for shlex support."""
        if isinstance(path, Path):
            path = str(path)
        return path.replace("\\", "/")

    def _get_docker_command(
            self,
            repo_path: Union[Path, str],
            relative_work_dir: Optional[str] = None
        ) -> str:
        """
        Create the docker portion of the command.

        Args:
            repo_path: Full path to the repo.
            relative_work_dir: Specific directory inside the repo to run the command in. Defaults to the root of the repo.
            mount_dir: Directory inside the Docker container where the repo will be mounted.
        """
        # Ready the repo path for the command
        sterilized_repo_path = DockerRunner.sterilize_path(repo_path)

        # Default to the root of the repo if no work dir is specified
        if relative_work_dir:
            relative_work_dir = DockerRunner.sterilize_path(relative_work_dir)
            absolute_work_dir = os.path.join(self.mount_dir, relative_work_dir)
        else:
            absolute_work_dir = self.mount_dir

        docker_portion = (
            "docker run "
            "--rm " # Remove the container after execution.
            f"-v {sterilized_repo_path}:{self.mount_dir} " # Mount repo folder into container.
            f"-w {absolute_work_dir} " # Set working directory inside container.
            f"{self.image}:{self.tag}" # Image and tag to use.
        )
        return docker_portion

    def _run_command(self, command: str, timeout: int) -> Tuple[int, str, str]:
        try:
            output = subprocess.run(shlex.split(command), capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            logging.error(f"Command timeout: {command}")
            return 1, "", "Timeout"

        stdout = output.stdout.decode("utf-8")
        stderr = output.stderr.decode("utf-8")
        return output.returncode, stdout, stderr
