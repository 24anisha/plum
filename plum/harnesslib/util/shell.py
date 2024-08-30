"""Utilities for running shell commands."""

from contextlib import contextmanager
from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
from typing import Union

from plum.harnesslib.data_model import ID


@dataclass
class ShellOutput:
    """
    Represents the output of a shell command
    """
    command_line: str
    """
    The command line used to launch the process, usually the space-separated concatenation of the
    `args`.
    """
    stdout: str
    "The standard output of the process"
    stderr: str
    "The standard error of the process"
    returncode: int
    "The return code of the process"
    id: ID = field(default=ID(-1), init=False)
    "The id of the `ShellOutput`"


def run_subprocess(args: list[str], shell: bool = False,
                   check: bool = False, timeout: Union[float, None] = None) -> ShellOutput:
    """
    Use subprocess.run to run a shell command and return the output.
    This uses subprocess.run in text mode, which means the output will be interpreted as strings.
    If `check = True` then throw an exception on non - zero return code. Otherwise, the return code
    is included in the `ShellOutput`.
    """
    command = ' '.join(args) if shell else args
    completed = subprocess.run(
        command,
        shell=shell,
        check=check,
        text=True,
        capture_output=True,
        timeout=timeout)
    return ShellOutput(
        command_line=" ".join(args),
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode
    )


@contextmanager
def change_cwd(new_path: Path):
    """
    Temporarily change the current working directory.
    Use as a context manager, i.e.
    ```
    with change_cwd(new_path):
        # do stuff with `cwd = new_path`
        ...
    # `cwd` is restored to its original value
    ```
    """
    old_path = os.getcwd()
    try:
        os.chdir(new_path)
        yield
    finally:
        os.chdir(old_path)
