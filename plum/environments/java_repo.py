import os
import logging
import shutil
from pathlib import Path
from enum import Enum
import subprocess

from plum.harnesslib.languages import Language
import plum.harnesslib.tasks as tasks

from plum.environments.repository import Repository
from plum.utils.logger import Logger

RepoType = Enum("RepoType", ['GITHUB', 'TEST', 'LOCAL'])

class JavaRepository(Repository):
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

        # Populated in get_gentest_directory with the location at which to write generated tests for the repository. 
        # Begins as None, becomes Path object if a location is found or "not_possible" if the 
        # repo structure won't allow us to programmatically find where to write tests
        self.test_write_location = None
        self.language = Language.Java
        self.stop_tokens.extend(["THEREISNOSTOPTOKEN"])

        self.comment_regexes = ['""".*?"""', "#.*?\n"]
        self._extensions = [".java"]


    def repo_init(self, cleanup, install_reqs):
        """
        Takes code generator object and:
        1. Clones the relevant repo if it's from GitHub
        """
        self.access_focal_code()


    def get_gentest_directory(self):
        """
        Traverse the directory tree starting from root_dir and return
        the first directory within src/test/java that has more than one
        additional directory within it.
        """
        # TODO replace with root_repo once eleanor's changes are pushed
        root_repo = self.base / self.internal_repo_path

        def count_subdirectories(directory):
            """
            Count the number of subdirectories in a given directory.
            """
            return sum(os.path.isdir(os.path.join(directory, name)) for name in os.listdir(directory))

        src_test_java_dir = os.path.join(root_repo, "src", "test", "java")

        # Check if src/test/java directory exists
        if not os.path.exists(src_test_java_dir):
            Logger().get_logger().error("src/test/java directory not found. Generated tests cannot be run.")
            self.test_write_location = "not_possible"

        else:
            for dirpath, dirnames, filenames in os.walk(src_test_java_dir):
                # Count the number of subdirectories in the current directory
                num_subdirectories = count_subdirectories(dirpath)
                if num_subdirectories > 1:
                    # TODO will it work if there aren't other files at that level?
                    self.test_write_location = Path(dirpath)
                    break
        
        # if we reach the end, and we haven't found any such directory, we cannot run generated tests
        if not self.test_write_location:
            self.test_write_location = "not_possible"

        return self.test_write_location


    def cleanup(self):
        """
        Delete the results of previous plum runs on a given repo.
        NOTE: Commented code works, but requires sudo permissions and 
        and rm -rf command, 
        """
        return "Not implemented, but needs to be for the ABC"
        # if self.repo_type.name == 'GITHUB' and os.path.exists(
        #     Path(self.base) / self.internal_repo_path
        # ):
        #     repo_path = str(Path(self.base) / self.internal_repo_path)

        #     subprocess.run(['sudo', 'rm', '-rf', repo_path], check=True)
        #     Logger().get_logger().info(f"{repo_path} has been successfully deleted with sudo privileges.")


