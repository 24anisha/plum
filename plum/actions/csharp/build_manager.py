from glob import glob
import logging
import os
from pathlib import Path
import re
import shlex
from typing import Union


from plum.actions._docker_runner import DockerRunner
from plum.actions.csharp._log_types import ErrorType
from plum.actions.csharp._ms_build_log_parser import BuildLog


class BuildManager:
    DEFAULT_BUILD_COMMAND = "dotnet build --no-incremental"
    """Command to build the project. Do not modify this directly.
    The `--no-incremental` flag is used to ensure that the build is not cached.
    """

    def __init__(
            self,
            repo_full_path: Union[Path, str],
            docker_runner: DockerRunner,
            timeout=60,
            retry_limit=3,
        ):
        """
        Args:
            repo_full_path: Full path to the repo to build.
            docker_work_dir: Working directory inside the Docker container.
            docker_image: Docker image to use for the build. If the wrong image is used, the manager will attempt to recover.
            docker_tag: Docker tag to use for the build. If the wrong image is used, the manager will attempt to recover.
            timeout: Timeout in seconds for the build command.
            retry_limit: Number of times to retry the build command.
        """
        ## Docker Configuration
        self.repo_path = repo_full_path
        self.docker = docker_runner

        ## Build Parameters
        self.timeout = timeout
        """Timeout in seconds for the build command."""
        self.retry_limit = retry_limit
        """Number of times to retry the build command."""
        self.timeout_increase = 5
        """Will multiply the timeout by this value if the build times out. NOTE: Beware of exponential growth!"""

        ## Build Command
        self.modified_command = None
        """Modified build command to use. Populated during auto recovery."""

    def build(self):
        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "attempt_details": [],
        }

        for i in range(self.retry_limit):
            logging.info(f"Build attempt {i + 1} of {self.retry_limit}: {self.repo_path}")
            command = self._create_shell_command()
            return_code, stdout, stderr = self.docker.run(
                command=command,
                repo_path=self.repo_path,
                timeout=self.timeout
            )

            result["attempt_details"].append({
                "attempt": i + 1,
                "return_code": return_code,
                "stdout": stdout,
                "stderr": stderr,
            })

            # Clean build, early return.
            # The MSBuild has a client/server split, however exit code 0 represents a successful build regardless.
            # https://github.com/dotnet/msbuild/blob/main/src/Build/BackEnd/Client/MSBuildClientExitType.cs#L6
            # https://github.com/dotnet/msbuild/blob/main/src/MSBuildTaskHost/OutOfProcTaskHost.cs#L29
            if return_code == 0:
                logging.info("Build process completed successfully")
                result["success"] = True
                result["stdout"] = stdout
                result["stderr"] = stderr
                return result

            # In case of timeout, just multiply the time frame.
            if stderr == "Timeout":
                new_timeout = self.timeout * self.timeout_increase
                logging.info(f"Build timeout, increasing timeout from {self.timeout}s to {new_timeout}s")
                self.timeout = new_timeout
                continue

            # Parse build output for errors (if your error parsing logic is here)
            build_log = BuildLog.parse(stdout)

            # Attempt to recover from known errors (if your error handling logic is here)
            auto_recovery_result = self._handle_known_errors(build_log.errors)

            # If none of the errors were solved, just exit out.
            if not any(solved for _, solved in auto_recovery_result):
                break

        # Set the final stdout and stderr after all attempts.
        result["stdout"] = stdout
        result["stderr"] = stderr

        # Report unsolved errors if the build wasn't successful.
        if not result["success"]:
            logging.error(
                f"Build failed: {self.repo_path}. "
                f"({self.docker.image}:{self.docker.tag}) "
                f"Errors: {build_log.errors}"
            )

        return result

    def _create_shell_command(self) -> str:
        """
        Change a list of commands into a single shell command.
        ex) sh -c "git config --global --add safe.directory /app && dotnet build"
        """
        commands = []

        # First add the git configuration command.
        commands.append(f"git config --global --add safe.directory {self.docker.mount_dir}")

        # Add the build command
        commands.append(self.modified_command if self.modified_command else BuildManager.DEFAULT_BUILD_COMMAND)

        joined_commands = " && ".join(commands)
        return f'sh -c "{joined_commands}"'


    def _handle_known_errors(self, errors: ErrorType):
        """Attempt to resolve known build errors. Assumes that there can be multiple errors."""
        solved = [] # Store whether each error was solved.

        for error in errors:
            if error.code == 'MSB1011':
                """
                MSB1011: Specify which project or solution file to use because this folder contains more than one project or solution file.

                This error occurs when there are multiple .sln files in the repo.
                Currently we just use the first .sln file we find.
                TODO: Later build all .sln files in a repo.
                """
                logging.info("Handling error MSB1011: Finding and specifying .sln file...")
                sln_files = glob(os.path.join(self.repo_path, '*.sln'))

                if not sln_files:
                    logging.error("No .sln file found for MSB1011 error recovery")
                    solved.append(False)
                    continue

                if len(sln_files) > 1:
                    logging.warning("Multiple .sln files found for MSB1011 error recovery. Building only the first one.")

                sln_file_name = shlex.quote(
                    # Only grab the file name and not the directory.
                    # The directory is already moved to self.docker_work_dir ("/app") in Docker.
                    os.path.basename(sln_files[0])
                )
                self.modified_command = f"{BuildManager.DEFAULT_BUILD_COMMAND} {sln_file_name}"
                solved.append(True)
                continue
            if error.code == 'MSB3644':
                """
                MSB3644: The reference assemblies for framework ".NETFramework,Version=vX.X" were not found.
                .NET Framework 4.8.1 can build most .NET 4.x.x projects.
                This hardcoded fix will handle most cases unless the repo is on .NET Framework 3.5.

                NOTE: The .NET Framework versions cannot be built outside of Windows environments.
                """
                logging.info("Handling error MSB3644: Using .NET Framework Docker image instead of .NET.")

                self.docker.image = 'mcr.microsoft.com/dotnet/framework/sdk'
                self.docker.tag = '4.8.1'
                solved.append(True)
                continue
            if error.code == 'NETSDK1045':
                """
                NETSDK1045: The current .NET SDK does not support targeting .NET X.0.

                This error occurs when the installed .NET SDK version does not match the .NET version specified by the project.
                Simply handled by using the correct Docker image.
                """
                dotnet_version = re.search(r'\.NET (\d+\.\d+)', error.message).group(1)
                logging.info(
                    "Handling error NETSDK1045: .NET version mismatch. "
                    f"Using {dotnet_version} Docker image instead of {self.docker.tag}."
                )

                self.docker.image = 'mcr.microsoft.com/dotnet/sdk'
                self.docker.tag = dotnet_version
                solved.append(True)
                continue

        return zip(errors, solved)
