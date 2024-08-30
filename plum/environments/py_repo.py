import os
import logging
import shutil
from pathlib import Path
from enum import Enum
import re

from plum.harnesslib.languages import Language
import plum.harnesslib.tasks as tasks

from plum.environments.repository import Repository
from plum.utils import fnhash, get_functions_from_file
from plum.utils.logger import Logger

RepoType = Enum("RepoType", ['GITHUB', 'TEST', 'LOCAL'])


class PythonRepository(Repository):
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
        self.language = Language.Python
        self.stop_tokens.extend(["THEREISNOSTOPTOKEN"])

        self.comment_regexes = ['""".*?"""', "#.*?\n"]
        self._excluded_paths.extend([
                     r'all_generated',
                     r'lib/site-packages$',
                     r'.venv$',
                     r'lib/python[0-9\.]+/site-packages$'])
        self._extensions = [".py"]
        if self.repo_type.name == 'GITHUB':
            self.env_path = (Path(self.base) / f"{str(self.internal_repo_path)}-venv").resolve()
        else:
            self.env_path = (Path(f"{str(self.base)}-venv")).resolve()

        self.interpreter_path = self.env_path / "bin/python"


    def repo_init(self, cleanup, install_reqs):
        """
        Takes code generator object and:
        1. Clones the relevant repo if it's from GitHub
        2. Installs required dependencies one by one 
                (will continue to install down the list even if some fail)
        3. Runs the tests to see if the original unit tests all run
        """
        self.access_focal_code()

        # if the user either wants to remove the existing venv or doesn't want to 
        # create it in the first place
        if (cleanup or not os.path.exists(self.env_path)) and install_reqs:

            environment = tasks.CreatePythonEnvironment(repo_info=self.repo, venv_path=self.env_path).execute()
            Logger().get_logger().warning("# Install any required dependencies.")
            installed_deps = tasks.install_dependencies(
                repo_info=self.repo,
                language=Language.Python,
                environment=environment
            ).execute()


    def get_test_functions(self):
        """
        Method to find all the test functions in the code
        & make a dictionary mapping test names to test bodies
        """
        # get functions without excluding test paths
        functions = self.walk_repository(get_functions_from_file)

        self.hash2test = {}
        for f in functions:
            if f.name in self.ignore_functions:
                continue
            # take all functions with test in function name or test as a directory in relative path
            if "test" in f.name or re.search(r'/test(s)?/', f.relative_path.lower) is not None:
                test_hash = fnhash(f)
                self.hash2test[test_hash] = f

        Logger().get_logger().warning("Found {} tests.".format(len(self.hash2test.keys())))
        return self.hash2test


    def cleanup(self):
        """
        Deletes the generated files for a fresh
        start before re-running code
        """

        # remove the virtual environment regardless
        if os.path.exists(self.env_path):
            Logger().get_logger().info("Deleting existing venv...")
            shutil.rmtree(self.env_path)
        
        # remove locally generated files
        if self.repo_type.name == 'TEST' or self.repo_type.name == 'LOCAL':
            removable_files = [
                "coverage",
                "all_generated"
            ]
            repo = Path(self.base) / self.repo_path
            for f in removable_files:
                if os.path.isdir(repo / f):
                    shutil.rmtree(repo / f)
                elif os.path.isfile(repo / f):
                    os.remove(repo / f)

        # delete git repo         
        elif self.repo_type.name == 'GITHUB' and os.path.exists(
            Path(self.base) / self.internal_repo_path
        ):
            shutil.rmtree(Path(self.base) / self.internal_repo_path)

