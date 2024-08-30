"Helper module for Python language support"

import sys
from typing import Optional, Union

from plum.harnesslib.data_model import Dependency
from plum.harnesslib.languages import Language
from plum.harnesslib.util.shell import ShellOutput, run_subprocess
import os
import toml
import glob
from plum.utils.logger import Logger


def python_subprocess(args: list[str],
                      check: bool = False, python_interpreter: Optional[str] = None,
                      timeout: Union[float, None] = None) -> ShellOutput:
    """
    Use subprocess.run to run a Python command and return the output.
    This uses the current Python executable to run the command.
    If `check = True` then throw an exception on non - zero return code. Otherwise, the return code
    is included in the `ShellOutput`.
    """
    if python_interpreter is None:
        python_interpreter = sys.executable
    return run_subprocess([python_interpreter] + args, check=check, timeout=timeout)


def pip_install(args: list[str],
                reason: str,
                python_interpreter: Optional[str] = None) -> list[Dependency]:
    "Run pip install with the given arguments"
    output = python_subprocess(['-m', 'pip', 'install', *args],
                               python_interpreter=python_interpreter)
    if output.returncode != 0:
        raise ValueError(
            f'pip install {args=} failed with {output.returncode=}\nStderr: {output.stderr}')
    # Parse the output of pip install to get the list of installed dependencies
    lines = output.stdout.splitlines()
    prefix = 'Successfully installed '
    dependencies: list[Dependency] = []
    for line in lines:
        if line.startswith(prefix):
            deps_str = line[len(prefix):].split(" ")
            for dep_str in deps_str:
                # Split on the last hyphen
                version_split = dep_str.rsplit('-', 1)
                if len(version_split) != 2:
                    continue
                pkg, version = version_split
                dependencies.append(Dependency(pkg, version, Language.Python, reason))
    return dependencies

def install_toml(interpreter_path: str, repo_root: str) -> None:
    # first check to see if has any optional dependencies that should be installed
    extras = None
    try:
        pyproject_toml_path = os.path.join(repo_root, "pyproject.toml")
        with open(pyproject_toml_path, "r") as pyproject_file:
                pyproject_contents = toml.load(pyproject_file)
                # Check for [project.optional-dependencies] and specifically for 'dev' dependencies
                optional_deps = pyproject_contents.get("project", {}).get(
                    "optional-dependencies", {}
                )
                if optional_deps:
                    Logger().get_logger().info(f"Optional dependencies found in the toml: {optional_deps}")
                if "dev" in optional_deps:
                   Logger().get_logger().info("dev dependencies found in the toml")
                   extras = "dev"
    except Exception as e:
        Logger().get_logger().error(f"Error reading {pyproject_toml_path}: {e}")

    # install using pip, use extras in dev dependencies found
    command = '' 
    if extras:
        command = [interpreter_path, "-m", "pip", "install", "-e" , repo_root + f"[{extras}]", "-vvv"]
    else:
        command = [interpreter_path, "-m", "pip", "install", "-e" , repo_root, "-vvv"]
    run_subprocess(
    command
    )
    Logger().get_logger().info("CREATE_VENV.PIP_INSTALLED_PYPROJECT")


def find_requirements_files(workspace_folder, exclude=None):
    # Prepare the exclude patterns by transforming them into a set for faster checks
    if exclude is not None:
        exclude = set(exclude)

    matched_files = []

    # Pattern for any file that includes "requirement" in its name
    pattern1 = os.path.join(workspace_folder, '**/*requirement*.txt')
    
    # Pattern for any file within a "requirements" folder
    pattern2 = os.path.join(workspace_folder, '**/requirements/*.txt')

    # Combine searches from both patterns
    for pattern in [pattern1, pattern2]:
        for file in glob.glob(pattern, recursive=True):
            if exclude:
                # Extract the relative path of the file to the workspace folder
                relative_path = os.path.relpath(file, workspace_folder)
                # Check if the relative path of the file starts with any of the exclude patterns
                if any(relative_path.startswith(ex) for ex in exclude):
                    continue
            matched_files.append(file)

    return matched_files