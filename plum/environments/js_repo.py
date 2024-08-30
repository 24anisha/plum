import os
import shutil
import logging
import json
from pathlib import Path
from enum import Enum
import subprocess

from pynpm import NPMPackage

import plum.harnesslib.tasks as tasks
from plum.harnesslib.languages import Language

from plum.utils import is_testable_file
from plum.utils import get_test_package
from plum.environments.repository import Repository
from plum.utils.logger import Logger


RepoType = Enum("RepoType", ['GITHUB', 'TEST', 'LOCAL'])

class JavascriptRepository(Repository):
    def __init__(
        self,
        base,
        repo_path="",
        commit_sha="",
        focal_functions=[],
        language="javascript"
        ):
        super().__init__(
            base, repo_path, commit_sha, focal_functions, language
        )
        self.pkg = None
        if language == "javascript":
            self.language = Language.Javascript
        elif language == "typescript":
            self.language = Language.Typescript
        
        self.stop_tokens.extend(["describe(", "```", "/*"])
        self.comment_regexes = ["/\/\*[\s\S]*?\*\/|([^:]|^)\/\/.*$"]
        
        self._excluded_paths.extend([
                        r'all_generated',
                        r'node_modules',
                        r'export_code_temp'])
        self.ignore_functions.append("anonymous")

        if language == "typescript":
            self._extensions = [".ts", ".tsx"]
        elif language == "javascript":
            self._extensions = [".js", ".jsx"]
        self.path2exports = {}


    def repo_init(self, cleanup, install_reqs):
        """
        Takes code generator object and:
        1. Clones the relevant repo if it's from GitHub
        2. Installs required dependencies
        """

        self.access_focal_code()
        Logger().get_logger().info(
            "# Install any required dependencies.",
            extra={
                "repo": self.repo_path
            })
        if install_reqs:
            self.install_requirements()

        pkg = os.path.join(
            self.base, self.internal_repo_path, "package.json")
        self.test_library = get_test_package(pkg)


    def overwrite_package_json(self, keys=('scripts','test'), command="jest", old_pkg_path='package_old_TEMP.json'):
        """
        rewrites the package.json file to change the command pointed to by keys
        :param keys: the value in the json to be changed in the package.json file
        :param command: the command to be inserted in place of the existing command
        :param old_pkg_path: the path to where the old contents of the package.json file should be written
        """
        # some potentially useful commands for the future (with typescript)
        # if self.language == Language.Typescript:
        #     pass_fail_cmd = "mocha -r ts-node/register"
            # if self.language == Language.Typescript:
            #     pkg_dict["scripts"]["build"] = "tsc"

        old_pkg = os.path.join(
            self.base, self.internal_repo_path, old_pkg_path
        )

        pkg = os.path.join(
            self.base, self.internal_repo_path, "package.json"
        )

        # read the original package.json file contents
        with open(pkg, "r") as package:
            pkg_dict = json.load(package)

        # if a package_old_TEMP.json exists, do not overwrite it.
        if not os.path.exists(old_pkg) and os.path.exists(pkg):
            with open(old_pkg, "w") as old_package:
                json.dump(pkg_dict, old_package)
        
        # write the new contents to the package.json
        with open(pkg, "w") as new_package:
            if len(keys) == 1:
                pkg_dict[keys[0]] = command
            elif len(keys) == 2 and keys[0] in pkg_dict:
                pkg_dict[keys[0]][keys[1]] = command
            json.dump(pkg_dict, new_package)


    def install_requirements(self):
        """
        Use the NPM Package class to install the dependencies for the given repo,
        as well as the dependencies that plum requires
        """

        installed_deps = tasks.install_dependencies(
            repo_info=self.repo, language=Language.Javascript
        ).execute()

        pkg = os.path.join(
            self.base, self.internal_repo_path, "package.json"
        )
        if not os.path.exists(pkg):
            raise Exception("A package.json file is required to generate tests for this repo. Please add a package.json file to the root of the repo.")
        
        self.pkg = NPMPackage(pkg)
        Logger().get_logger().info("installing js packages...")

        install_status = self.pkg.install("mocha@10.2.0", "chai@4.3.7", "jest@29.5.0", "ts-morph@17.0.1", "nyc@15.1.0", "mocha-json-output-reporter@2.1.0")
        
        # check to comfirn the additional required packages were successfully installed. Otherwise, throw an error
        if install_status != 0:
            raise ValueError("Unable to install javascript packages necessary to PLUM functionality")
        
        if self.language == Language.Typescript:
            Logger().get_logger().info("installing ts packages...")

            install_status = self.pkg.install("ts-node", "@types/chai", "@types/mocha")
            if install_status != 0:
                raise ValueError("Unable to install typescript packages necessary to PLUM functionality")



    def rewrite_package_json(self, old_pkg_path='package_old_TEMP.json'):
        old_pkg = os.path.join(
            self.base, self.internal_repo_path, old_pkg_path
        )
        pkg = os.path.join(
            self.base, self.internal_repo_path, "package.json"
        )

        with open(old_pkg, "r") as og_package:
            pkg_dict = json.load(og_package)

        with open(pkg, "w") as package:
            json.dump(pkg_dict, package)


    def get_testable_files(self):
        """
        Returns a list of all the files in the repo that are testable
        """

        test_library = self.test_library if self.test_library else "jest"
        self.overwrite_package_json(command=test_library)
        if self.test_library == "jest":
            self.overwrite_package_json(keys=('jest','testRegex'), command="")
        testable_files = self.walk_repository(is_testable_file)
        self.rewrite_package_json()

        return testable_files


    def cleanup(self):
        """
        Deletes the generated files for a fresh
        start before re-running code
        """
        if self.repo_type.name == 'TEST' or self.repo_type.name == 'LOCAL':
            removable_files = [
                "node_modules",
                ".nyc_output"
                "all_generated",
                "coverage",
                "mochawesome-report",
                "package-lock.json",
                "export_code_TEMP"
            ]
            repo = Path(self.base) / self.repo_path
            for f in removable_files:
                if os.path.isdir(repo / f):
                    shutil.rmtree(repo / f)
                elif os.path.isfile(repo / f):
                    os.remove(repo / f)

        elif self.repo_type.name == 'GITHUB' and os.path.exists(
            Path(self.base) / self.internal_repo_path
        ):
            shutil.rmtree(Path(self.base) / self.internal_repo_path)
        
