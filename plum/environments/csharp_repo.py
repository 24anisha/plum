import os
import logging
import shutil
from pathlib import Path
from enum import Enum

from plum.harnesslib.languages import Language
import plum.harnesslib.tasks as tasks

from plum.environments.repository import Repository

RepoType = Enum("RepoType", ['GITHUB', 'TEST', 'LOCAL'])


class CsharpRepository(Repository):
    def __init__(
        self,
        base,
        repo_path="",
        commit_sha="",
        focal_functions=[],
        language=None
    ):
        super().__init__(
            base, repo_path, commit_sha, focal_functions, language
        )
        self.language = Language.Csharp
        self.stop_tokens.extend(["THEREISNOSTOPTOKEN"])

        self.comment_regexes = ['""".*?"""', "#.*?\n"]
        self._extensions = [".cs"]


    def repo_init(self, cleanup, install_reqs):
        """
        Takes code generator object and:
        1. Clones the relevant repo if it's from GitHub
        """
        self.access_focal_code()


    def cleanup(self):
        # Deleting entire repo if cleanup is true
        # Generated files cannot be deleted here, since they need to be deleted from a docker command due to permission levels
        shutil.rmtree(Path(self.base) / self.internal_repo_path)


