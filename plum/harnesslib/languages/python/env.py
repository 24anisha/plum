"""Representation of Python venv"""

import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from plum.harnesslib.data_model.base import DataModel
from plum.harnesslib.languages.python.helpers import python_subprocess
from plum.harnesslib.data_model import ClonedRepoInfo
from plum.harnesslib.tasks.task import SingleResultTask


@dataclass
class PythonEnvironment(DataModel):
    "Represents an environment and interpreter to run repos and tests with."

    interpreter_path: Path
    "Absolute path to the Python interpreter for the venv"

    venv_path: Optional[Path] = None
    "Absolute path to the venv"

    def __post_init__(self):
        if not self.interpreter_path.is_absolute():
            raise ValueError("interpreter_path must be absolute")
        if self.venv_path is not None and not self.venv_path.is_absolute():
            raise ValueError("venv_path must be absolute")


class CreatePythonEnvironment(SingleResultTask[PythonEnvironment]):
    """Task to create a Python venv for a given repo."""

    def __init__(self, repo_info: ClonedRepoInfo, venv_path: Optional[Path] = None):
        self.repo_info = repo_info

        if venv_path is None:
            self.venv_path = (self.repo_info.clone_path.parent /
                              (self.repo_info.clone_path.name + '-venv')).resolve()
        else:
            self.venv_path = venv_path

        if not self.venv_path.is_absolute():
            raise ValueError("venv_path must be absolute")

    def execute(self, ) -> PythonEnvironment:
        interpreter_path = self.venv_path / 'bin/python'
        if not interpreter_path.exists():
            result = python_subprocess(['-m', 'venv', self.venv_path.as_posix()])
            if result.returncode != 0:
                return PythonEnvironment(venv_path=None, interpreter_path=Path(sys.executable))
        return PythonEnvironment(venv_path=self.venv_path, interpreter_path=interpreter_path)
