from glob import glob
import logging
import os
from pathlib import Path
import re
from typing import List, Union


from plum.actions._docker_runner import DockerRunner
from plum.actions.csharp._sln_parser import Solution, CsProj
from plum.utils.cobertura import parse_xml_as_dict


class CoverageManager:
    COVERAGE_INSTALL_COMMAND = "dotnet add package coverlet.collector"
    """Command to install the coverlet collector package. Do not modify unless the dotnet CLI changes."""

    # NOTE: This command will also build the project.
    # However due to our --rm design of the DockerRunner, using the --no-build flag will not work.
    COVERAGE_COMMAND = "dotnet test --collect:'XPlat Code Coverage'"
    """Command to run the coverage command. Do not modify unless the dotnet CLI changes."""

    _ARTIFACT_REGEX = re.compile(r'Attachments:\s+(.*)')
    """The regex to find individual coverage artifacts from the log."""

    _MERGED_REPORT_REGEX = re.compile(r'Merged into file\s+(.*)\.')
    """The regex to find the merged coverage report from the log."""

    @staticmethod
    def load(
        repo_full_path: Union[Path, str],
        docker_runner: DockerRunner,
        timeout=60,
    ):
        """
        Scan the solution file, find all test projects, check Coverlet status.
        Initialize and return a CoverageManager instance with this data.

        Args:
            repo_full_path: Full path to the repo containing the .sln file.

        Returns:
            Dictionary with 'success', 'error', and 'manager' keys.
        """
        # Initialize the result dictionary
        result = {"success": False, "error": None, "manager": None}

        try:
            # Find the .sln file.
            sln_files = glob(os.path.join(repo_full_path, '*.sln'))

            if not sln_files:
                raise FileNotFoundError("No .sln file found for code coverage generation.")

            if len(sln_files) > 1:
                logging.warning("Multiple .sln files found for code coverage generation. Using only the first one.")

            # Parse .sln file and find test projects.
            solution_path = os.path.join(repo_full_path, sln_files[0])
            solution = Solution.from_file(solution_path)
            test_projects = solution.get_test_projects()

            manager = CoverageManager(
                repo_full_path=repo_full_path,
                root_solution=solution,
                test_projects=test_projects,
                docker_runner=docker_runner,
                timeout=timeout,
            )

            # Update the result dictionary with success and the manager
            result["success"] = True
            result["manager"] = manager

            return result

        except Exception as e:
            # Log the error and update the result dictionary
            logging.error(f"Error loading CoverageManager: {e}")
            result["error"] = str(e)
            return result

    def __init__(
            self,
            repo_full_path: Union[Path, str],
            root_solution: Solution,
            test_projects: List[CsProj],
            docker_runner: DockerRunner,
            timeout=60,
        ):
        """
        Args:
            repo_full_path: Full path to the repo to build.
            docker_work_dir: Working directory inside the Docker container.
            docker_image: Docker image to use for the build.
            docker_tag: Docker tag to use for the build.
            timeout: Timeout in seconds for the build command.
            retry_limit: Number of times to retry the build command.
        """
        ## Docker Configuration
        self.repo_path = repo_full_path
        self.docker = docker_runner

        self.root_solution = root_solution
        """Solution object for the given solution. TODO: Not sure if this is necessary."""
        self.test_projects = test_projects
        """List of test projects inside the given solution."""

        ## Build Parameters
        self.timeout = timeout
        """Timeout in seconds for the build command."""

    def install_coverlet(self):
        """
        Install the Coverlet collector package.

        Returns:
            Dictionary with the following keys:
            - success: Whether the Coverlet installation was successful.
            - failed_projects: List of projects for which the Coverlet installation failed.
        """
        result = {
            "success": True,
            "failed_projects": [],
        }

        for test_project in self.test_projects:
            relative_work_dir = str(Path(test_project.path).parent)

            return_code, stdout, stderr = self.docker.run(
                command=CoverageManager.COVERAGE_INSTALL_COMMAND,
                repo_path=self.repo_path,
                relative_work_dir=relative_work_dir,
                timeout=self.timeout,
            )

            if return_code != 0:
                logging.error(f"Failed to install Coverlet for project {test_project.name}.")
                result["failed_projects"].append({
                    "project": test_project.name,
                    "error": f"Return code {return_code}",
                    "stdout": stdout,
                    "stderr": stderr,
                })
                result["success"] = False

        return result

    def run_coverage(self):
        """
        Run the coverage command.

        Returns:
            Dictionary with the following keys:
            - success: Whether the coverage command was successful.
            - error: Error message if the coverage command failed.
            - coverage_data: Dictionary of coverage data, with the keys being the project path relative to root.
        """
        result = {
            "success": False,
            "error": None,
            "coverage_data": {},
            "failed_projects": [],
        }

        try:
            # Run the coverage command for each test project.
            failed_projects = []
            for test_project in self.test_projects:
                relative_work_dir = str(Path(test_project.path).parent)

                return_code, stdout, stderr = self.docker.run_multi_command(
                    commands=[
                        CoverageManager.COVERAGE_INSTALL_COMMAND,
                        CoverageManager.COVERAGE_COMMAND,
                    ],
                    repo_path=self.repo_path,
                    relative_work_dir=relative_work_dir,
                    timeout=self.timeout,
                )

                if return_code != 0:
                    result["failed_projects"].append({
                        "project": test_project.name,
                        "error": f"Return code {return_code}",
                        "stdout": stdout,
                        "stderr": stderr,
                    })

            # Merge the coverage reports from all the test projects.
            merge_commands = [
                "dotnet tool install --global dotnet-coverage",
                "/root/.dotnet/tools/dotnet-coverage merge --remove-input-files **/*.cobertura.xml -f cobertura"
            ]
            return_code, stdout, stderr = self.docker.run_multi_command(
                commands=merge_commands,
                repo_path=self.repo_path,
                timeout=self.timeout,
            )

            # Find the coverage artifact.
            matches = CoverageManager._MERGED_REPORT_REGEX.findall(stdout)
            if not matches:
                result["error"] = "No coverage artifacts found."
                return result

            # Process each found artifact.
            for artifact_path in matches:
                rel_path = Path(artifact_path).relative_to(self.docker.mount_dir)
                local_path = self._docker_to_local_path(artifact_path)

                coverage = parse_xml_as_dict(local_path)
                coverage = self._adapt_cobertura_report(coverage)

                result["coverage_data"][str(rel_path.parent)] = coverage

            result["success"] = True
        except Exception as e:
            result["error"] = str(e)

        return result

    def _docker_to_local_path(self, docker_path: str) -> str:
        """
        Convert a path inside the Docker container to a path on the local machine.

        Args:
            docker_path: Path to convert.

        Returns:
            Converted path.
        """
        rel_path = Path(docker_path).relative_to(self.docker.mount_dir)
        local_path = Path(self.repo_path).joinpath(rel_path)
        return str(local_path)

    # TODO: Java has this same method. Refactor to a common method.
    def _adapt_cobertura_report(self, report: dict):
        """
        Adapt the cobertura report to the format that the coverage report expects.

        Mainly carries out two operations.
        1. Renames the sources
            The sources point to the docker mount path, which is not the local full path.
            ex) old: /app/src/MediatR/
            ex) new: /datadisk/src/tmp/MediatR/src/MediatR
        """
        # Check for multiproject repos
        if '.' in report:
            if len(report) > 1:
                logging.warning(f"Found multiple projects in the coverage report. Using aggregated report.")
            report = report['.']

        # Change the Cobertura source paths to point to the repo full path instead of the docker mount path.
        if isinstance(report['coverage']['sources']['source'], str):
            new_source = self._docker_to_local_path(report['coverage']['sources']['source'])
            report['coverage']['sources']['source'] = new_source
            new_sources = [new_source]
        else:
            new_sources = []
            for source in report['coverage']['sources']['source']:
                # The source states docker work dir, replace it with the repo full dir.
                if source.startswith(self.docker.mount_dir):
                    source = self._docker_to_local_path(source)
                new_sources.append(source)
            report['coverage']['sources']['source'] = new_sources

        # Change the Cobertura packages to point to the repo full path instead of the docker mount path.
        packages = report['coverage']['packages']['package']
        if isinstance(packages, dict):
            packages = [packages]

        for package in packages:
            file_dicts = package['classes']['class']
            if isinstance(file_dicts, dict):
                file_dicts = [file_dicts]

            for f in file_dicts:
                filepath = f.get('@filename')

                for source in new_sources:
                    potential_path = Path(source) / filepath
                    if potential_path.exists():
                        f['@filename'] = str(potential_path.relative_to(self.repo_path))
                        break

        return report