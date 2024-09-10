import os
import re
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

from tree_sitter import Language as L

from plum.harnesslib.languages import Language
from plum.harnesslib.data_model import (
    ClonedRepoInfo
)
from plum.utils import (
    clone_repository,
    get_head_commit_hash,
    get_functions_from_file,
    fnhash
)
from plum.utils.logger import Logger


RepoType = Enum("RepoType", ['GITHUB', 'TEST', 'LOCAL'])

"""Return code from Linux's timeout command when given command times out"""
TIMEOUT_RETURNCODE = 124

class Repository(ABC):
    def __init__(
        self,
        base,
        repo_path="",
        commit_sha="",    
        focal_functions=[],
        language=None
                ):
        """
        Initialize a Repository Object
        :param base: path to the base directory where GitHub repos will be cloned.
        :param repo_path: For GitHub repos, repo_path is the "username/reponame".
                          For Local repos (i.e. pointing to an existing directory
                          that you don't want to clone again), it should be ""
        :param commit_sha: commit hash of the commit you want to clone for the git repo
        :param focal_functions: list of previously calculated function objects to consider
                                for a repo (in case the user only wants to consider a subset)
        :param language: optional keyword. Used for javascript vs. typescript, since they both
                         utilize the JavascriptRepository object.
        :param repo_root: path to the root of the focal repo (saved here rather than 
                                                            recalculating all the time)
        """
        # ATTRIBUTES SET IN PARENT CLASS #
        self.repo_path = Path(repo_path)
        """
        If a github repo, then "username/reponame"
        If a local repo, then nothing
        """

        self.base = Path(base).resolve()
        """
        The user can pass in a non-absolute path, but we will set it to
        an absolute path here regardless
        """

        if repo_path == "":
            self.repo_type = RepoType.LOCAL

        else:
            self.repo_type = RepoType.GITHUB

        self.is_cloned = os.path.exists(self.base / str(self.repo_path).replace("/", "--"))
        self.commit_sha = commit_sha
        self.stop_tokens = []
        self.focal_functions = focal_functions
        self.language = language

        # ATTRIBUTES SET IN CHILD CLASS #
        self.repo = None
        if self.repo_type.name == 'GITHUB':
            self.internal_repo_path = str(self.repo_path).replace("/", "--") 
        else:
            self.internal_repo_path = str(self.repo_path)
       
        self.repo_root = (self.base / self.internal_repo_path)

        self.test_runner = None
        self.all_tests = {}
        self.language = None
        self.parser = None
        self.comment_regexes = None
        self.ignore_functions = [""]

        # ATTRIBUTES THAT CAN BE RESET IN CHILD CLASS #
        self.rel_path2file_str = {}
        self._excluded_paths = []


    def setup(self, cleanup=False, install_reqs=True, all_reqs=False):
        """
        Calls all the setup functions for a code generator
        :param cleanup: If True, will remove the cloned repo
        :param install_reqs: If True, will install the required dependencies one by one
        :param all_reqs: If True, will install all the dependencies at once
        """
        if cleanup:
            self.cleanup()
            self.is_cloned = False

        self.repo_init(cleanup, install_reqs)


    def repo_init(self, cleanup, install_reqs):
        """
        Takes repo path and:
        1. Clones the repo if it's from GitHub
        2. Installs required dependencies
        3. Runs the tests to see if the original unit tests all run
        """
        pass

    def access_focal_code(self):
        """
        Helper method to either clone github repo if test_repo == False,
        or assume the path is to a test directory and create
        a ClonedRepoInfo object, rather than cloning from GitHub
        """
        if self.repo_type.name == 'LOCAL':
            repo = ClonedRepoInfo(
                language=self.language,
                owner="",
                repo_name=self.base.name,
                folder_name=self.base.name,
                clone_path=self.base,
                commit_sha=self.commit_sha
            )
        # elif self.repo_type.name == 'TEST':
        #     # if it a test repo inside the plum-api
        #     # create a repo with the information
        #     repo_name = str(self.repo_path).split("/")[-1:]

        #     clone_dir = self.repo_path
        #     repo = ClonedRepoInfo(
        #         language=self.language,
        #         owner="",
        #         repo_name=repo_name,
        #         folder_name=repo_name,
        #         clone_path=clone_dir,
        #         commit_sha=self.commit_sha
        #     )

        # if it's a github repo (cloned or not)
        elif self.repo_type.name == 'GITHUB':
            owner, repo_name = str(self.repo_path).split("/")[-2:]
            clone_dir = Path(self.base) / self.internal_repo_path

            if self.is_cloned:
                repo = ClonedRepoInfo(
                    language=self.language,
                    owner=owner,
                    repo_name=repo_name,
                    folder_name=repo_name,
                    clone_path=clone_dir,
                    commit_sha=self.commit_sha
                )

            else:
                # if it's not a test repo, clone the repo
                # create a repo with the information of the cloned repo
                clone_path = "https://github.com/" + str(self.repo_path)
                result = clone_repository(clone_path, clone_dir, commit=self.commit_sha)
                if result == TIMEOUT_RETURNCODE:
                    Logger().get_logger().error("ERROR: timeout occurred when attempting to clone, failed to clone")
                repo = ClonedRepoInfo(
                    language=self.language,
                    owner=owner,
                    repo_name=repo_name,
                    folder_name=repo_name,
                    clone_path=clone_dir,
                    commit_sha=self.commit_sha
                )

            if self.commit_sha == "":
                self.commit_sha = get_head_commit_hash(clone_dir)

        self.repo = repo


    def get_functions(self):
        """
        Walk through all the files in a repository and get all the
        functions as Function objects
        :returns: Dict of function hash: Function objects
        """
        functions = self.walk_repository(get_functions_from_file, additional_excluded_paths=[r'test(s)?/'])

        # only looks at the functions specified by the user
        if len(self.focal_functions) != 0:
            functions = [f for f in functions if f.name in self.focal_functions]

        self.hash2function = {}
        for f in functions:
            if f.name in self.ignore_functions or "test" in f.name.lower():
                continue
            else:
                func_hash = fnhash(f)
                self.hash2function[func_hash] = f

        Logger().get_logger().warning("Found {} functions.".format(len(self.hash2function.keys())))
        return self.hash2function


    def walk_repository(self, fn, additional_excluded_paths=[]):
        """
        Walk through the files in the repository and,
        based on the passed in function, parse each file using 
        the respective function
        :param fn: Function applied to each file. One of:
            - get_functions_from_file
            - is_testable_file
            - get_exports
        :param additional_excluded_paths: Additional paths to exclude (useful for getting
            functions from files in a repo, but excluding the test files)
        :return: List of results (dependent upon the function)
        """
        excluded_paths = self._excluded_paths
        excluded_paths.extend(additional_excluded_paths)

        queue = [self.repo_root]
        results = []
        while len(queue) > 0:
            file_path = Path(queue.pop())
            path_to_match = file_path.relative_to(self.repo_root).as_posix().lower()
            if any(re.search(excluded, path_to_match) is not None for excluded in excluded_paths):
                continue
            if file_path.is_dir():
                queue.extend(file_path.iterdir())
            elif file_path.is_file() and file_path.suffix in self._extensions:

                results.extend(fn(self, file_path))

        return results


    @abstractmethod
    def cleanup():
        pass