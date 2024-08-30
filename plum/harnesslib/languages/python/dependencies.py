"""
Helpers for installing dependencies to set up a python repo.
"""
import sys
from pathlib import Path

from plum.harnesslib.data_model import ClonedRepoInfo, Dependency
from plum.harnesslib.languages.python.env import PythonEnvironment
from plum.harnesslib.tasks.dependencies import DependencyInstaller
from plum.harnesslib.util.shell import run_subprocess
from plum.harnesslib.languages.python.helpers import (
    pip_install,
    install_toml,
    find_requirements_files,
)
import os
from plum.utils.logger import Logger


PACKAGES_TO_IGNORE = [
    'pkg-resources==0.0.0',  # pip freeze artifact
]

PACKAGES_TO_REPLACE = {'grpc': 'grpcio'}

# Anything listed here would get installed before listed dependencies.
# There are some one-off cases e.g. cmake and Cython, but I haven't seen any
# packages that seem systematically missing across repos. So this is an empty list for now
# but we can add to it in the future if we do identify commonly missing dependencies.
PACKAGES_TO_INSTALL = []


class PythonRepoDependencyInstaller(DependencyInstaller):
    """
    Dependency installer for Python.
    """

    repo_info: ClonedRepoInfo
    "The cloned repo in which to install dependencies"

    def __init__(self,
                 repo_info: ClonedRepoInfo,
                 environment: PythonEnvironment = PythonEnvironment(
                     interpreter_path=Path(sys.executable))):
        self.python_path = environment.interpreter_path.as_posix()

        super().__init__(repo_info)

    def install_runner_dependencies(self) -> list[Dependency]:
        "Install dependencies needed for test runner"
        return pip_install(
            ['-U', 'coverage', 'pytest', 'pytest-timeout', 'pytest-json-report'],
            "test_runner_dependencies",
            python_interpreter=self.python_path
        )

    def install_from_setup_py(self) -> list[Dependency]:
        "Install dependencies listed in setup.py"
        repo_path = self.repo_info.clone_path
        if not (repo_path / 'setup.py').exists():
            return []
        return (
            pip_install(
                ['-e', str(repo_path)], 'setup.py',
                python_interpreter=self.python_path)
            + pip_install(
                ['-e', f'{str(repo_path)}[dev]'], 'setup.py[dev]',
                python_interpreter=self.python_path)
            + pip_install(
                ['-e', f'{str(repo_path)}[test]'], 'setup.py[test]',
                python_interpreter=self.python_path))

    def _install_package(self,
                         line: str,
                         source: str) -> list[Dependency]:
        "Install a single dependency"
        # Checks if a package belongs to a known set of packages that are deprecated.
        # For example, the error message for grpc tells users to install grpcio instead.
        if line in PACKAGES_TO_REPLACE.keys():
            line = PACKAGES_TO_REPLACE[line]
        try:
            return pip_install(['-U', line], source, python_interpreter=self.python_path)
        except ValueError:
            # In some cases there are conflicts between the pinned package version
            # and other dependencies, or the specified version simply doesn't exist.
            # If possible, we try installing an unpinned version and let the pip
            # package manager resolve the conflict.
            # For example, if numpy==1.2 fails, we try installing just numpy.
            if '==' in line:
                return pip_install(
                    ['-U', line.split('==')[0]], source, python_interpreter=self.python_path)
            elif '>=' in line:
                return pip_install(
                    ['-U', line.split('>=')[0]], source, python_interpreter=self.python_path)
        return []

    def install_from_requirements(self) -> list[Dependency]:
        # find any requirements.txt files in the repo
        ## TODO Debug 
        # requirements_files = find_requirements_files(self.repo_info.clone_path)
        # Logger().get_logger().info(f"Found requirements files: {requirements_files}")
        # args = ["-e", "."]
        # for req_file in requirements_files:
        #     args.extend(["-r", req_file])
        # return pip_install(
        #     args, "requirements.txt glob search", python_interpreter=self.python_path
        # )
        "Install dependencies from requirements.txt and requirements_test.txt"
        # Install requirements line by line to ignore failure
        deps: list[Dependency] = []
        for requirements_file in ['requirements.txt', 'requirements_test.txt']:
            requirements_path = self.repo_info.clone_path / requirements_file
            if requirements_path.exists():
                with requirements_path.open('rb') as f:
                    for line in f:
                        line = line.decode('utf-8').strip()
                        if (len(line) > 0 and
                            not line.startswith('#') and
                                not any(pkg in line for pkg in PACKAGES_TO_IGNORE)):
                            deps.extend(
                                self._install_package(line, requirements_file))

        return deps


    def install_by_pipreqs(self) -> list[Dependency]:
        "Install dependencies by polling pipreqs"
        # Manufacture dependencies from sources and install those too
        deps = pip_install(['-U', 'pipreqs'], "pipreqs")
        pipreqs_output = run_subprocess(
            ['pipreqs', '--mode', 'no-pin', '--print', str(self.repo_info.clone_path)])
        for req in pipreqs_output.stdout.splitlines():
            stripped = req.strip()
            if stripped != '' and not any(pkg in stripped for pkg in PACKAGES_TO_IGNORE):
                deps.extend(self._install_package(stripped, 'pipreqs'))

        return deps

    def install_pytest(self) -> list[Dependency]:
        """
        Install pytest

        pytest is not necessarily a dependency for the repo itself, but is used by harnesslib.
        TODO: Consider not installing pytest in this task.
        """
        return pip_install(
            ['-U', 'pytest', 'pytest-timeout'], "pytest", python_interpreter=self.python_path)

    def execute(self) -> list[Dependency]:
        "Install the dependencies"
        deps: list[Dependency] = []
        any_success = False
        failures: dict[str, Exception] = {}

        for pkg in PACKAGES_TO_INSTALL:  # type: ignore
            deps.extend(pip_install(['-U', pkg], 'hs_defaults', self.python_path))
        
        # toml
        repo_root: Path = self.repo_info.clone_path

        try:
            if (repo_root / "pyproject.toml").exists():
                install_toml(os.fspath(self.python_path), str(repo_root))
                any_success |= True
        except Exception as e:
            failures["pyproject.toml"] = e
            Logger().get_logger().error("Failed installing from pyproject.toml")

        try:
            deps.extend(self.install_from_setup_py())
            any_success |= True
        except Exception as e:
            failures['setup.py'] = e
            Logger().get_logger().error('Failed installing from setup.py')

        try:
            deps.extend(self.install_from_requirements())
            any_success |= True
        except Exception as e:
            failures['requirements.txt'] = e
            Logger().get_logger().error('Failed installing from requirements.txt')

        try:
            deps.extend(self.install_by_pipreqs())
            any_success |= True
        except Exception as e:
            failures['pipreqs'] = e
            Logger().get_logger().error('Failed installing from pipreqs')

        try:
            deps.extend(self.install_runner_dependencies())
        except Exception as e:
            failures["test_runner_dependencies"] = e
            Logger().get_logger().error('Failed installing test runner dependencies')

        if not any_success:
            raise Exception('Failed to install dependencies: {}'.format(failures))

        return deps
