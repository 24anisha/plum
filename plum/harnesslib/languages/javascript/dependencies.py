import json

from plum.harnesslib.data_model import ClonedRepoInfo, Dependency
from plum.harnesslib.tasks.dependencies import DependencyInstaller
from plum.harnesslib.languages import Language
from plum.harnesslib.util.context_managers import temporary_path_change_to
from plum.harnesslib.util.shell import run_subprocess, ShellOutput


class JavascriptRepoDependencyInstaller(DependencyInstaller):
    """
    Dependency installer for Javascript.
    """
    repo_info: ClonedRepoInfo

    def __init__(self, repo_info: ClonedRepoInfo):
        super().__init__(repo_info)

    def parse_deps_text(self, npm_output: str) -> list[Dependency]:
        """Parse output from npm ls to generate list of dependencies
        Args:
            npm_output (str): output from npm ls
        Returns:
            list[Dependency]: List of dependencies
        """
        VERSION = "version"

        deps: list[Dependency] = []

        for package_name, package_info in json.loads(npm_output)["dependencies"].items():
            deps.append(
                Dependency(
                    package_name,
                    package_info[VERSION],
                    language=Language.Javascript,
                    reason=""
                )
            )

        return deps

    def install_using_npm(self) -> ShellOutput:
        """Install dependencies using npm
        Returns:
            ShellOutput: ShellOutput object containing result of running npm install
        """
        with temporary_path_change_to(str(self.repo_info.clone_path)):
            return run_subprocess(
                ["npm", "install"]
            )

    def install_using_yarn(self) -> ShellOutput:
        """Install dependencies using yarn
        Returns:
            ShellOutput: ShellOutput object containing result of running yarn install
        """
        with temporary_path_change_to(str(self.repo_info.clone_path)):
            return run_subprocess(
                ["npx", "yarn", "install"]
            )

    def get_dependencies(self) -> list[Dependency]:
        """Get list of dependencies installed
        Raises:
            ValueError: If running npm ls throws error
        Returns:
            list[Dependency]: list of installed dependencies
        """
        with temporary_path_change_to(str(self.repo_info.clone_path)):
            subproc = run_subprocess(
                ["npm", "ls", "--json"]
            )
        if subproc.returncode == 0:
            return self.parse_deps_text(subproc.stdout)
        else:
            raise ValueError(f"Unable to list dependencies. Error: {subproc.stderr}")

    def execute(self) -> list[Dependency]:
        """Install dependencies"""
        subproc = self.install_using_npm()
        # if subproc.returncode != 0:
        #     subproc = self.install_using_yarn()

        if subproc.returncode != 0:
            raise ValueError(f"Unable to install dependencies. Error: {subproc.stderr}")

        return self.get_dependencies()
