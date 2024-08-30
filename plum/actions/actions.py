import os
import re
import logging
from dataclasses import dataclass
import fileinput
from abc import ABC, abstractmethod

from plum.harnesslib.languages import Language
from plum.utils.logger import Logger

import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential  
)


class Actions():
    """
    Base class used to represent the actions that can be taken on an environment object

    Attributes:
    -----------
    environment: the environment object that we are taking actions on
                Could be a repository, a directory, etc etc.

    """
    def __init__(
        self,
        environment):
        self.environment = environment

    # TODO these abstract method decorators are a breaking change to CES because 
    # we use run_test right now. Does any code there need to be fixed?
    # @abstractmethod
    def run_test_suite(self, timeout=30):
        """
        Run the existing test suite of the 
        
        :return: report of which tests passed and failed
            (report specs are dependent on language and which
            testing library the given repo uses)
        """
        pass
    
    # @abstractmethod
    def get_coverage(self):
        """
        Get list of focal functions with coverage, and what percentage
        of the lines in the function are covered
        :return: dictionary mapping function hash to coverage percentage
        """
        pass

        # TODO add run_generated_test as an abstract method of the actions class
    # @abstractmethod
    # def run_generated_test(self, generated_test)

    # @abstractmethod
    # def run_single_test(self, test_file_path):
    #     """
    #     Given a path to a file with a test in it, 
    #     evaluate the test in the given repo context and return
    #     a single output in the form
    #     {path: path_to_generated_test, 
    #         success: True/False of test passing
    #         stdout: stdout of running npm test
    #         stderr: stderror of running npm test
    #     }
    #     """

    #     pass


    def create_file(self, path, filename, content):
        """
        Create a file in the environment and write the content
        params: 
        :path: the path to the file
        :filename: the name of the file
        :content: the content to be written into the file
        """
        try:
            os.chdir(path)
            with open(filename, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            Logger().get_logger().exception(e)
            return False


    def write_snippet_to_file(self, snippet, file_path, snippet_type='function'):
        """
        Write a snippet to a file
        params: 
        :snippet_text: the content to be written into the file
        :path: the path to the file
        :snippet: the type of snippet to be written (function, docstring, lines of code, etc)
        """
        if snippet_type == 'function':
            function = ""
            # if snippet is a function, we need to build and write the function
            if snippet.docstring:
                if self.environment.language == Language.Javascript or self.environment.language == Language.Typescript:
                    function += f'/*\n{snippet.docstring}\n*/'
                elif self.environment.language == Language.Python:
                    function += f'"""\n{snippet.docstring}\n"""'
            if snippet.signature:
                function += f"\n{snippet.signature}\n"
            if snippet.body:
                function += f"\n{snippet.body}\n"

            # TODO add decorators/attributes 
        with fileinput.FileInput(file_path, inplace=True) as file:
            for line_number, line in enumerate(file, start=0):
                # if it's the code to be deleted, skip it
                if line_number >= snippet.start_line and line_number <= snippet.end_line:
                    continue
                elif line_number == snippet.end_line + 1:
                    print(function, end='\n')
                else:
                    print(line, end='')


    def save_generated_tests(self, fnhash, full_tests):
        """
        Create a file that we put each
        generated test into, one by one
        Add generated test to dictionary with all generated tests
        """
        if self.language == Language.Javascript:
            extension = ".js"
        elif self.language == Language.Python:
            extension = ".py"
        elif self.language == Language.Typescript:
            extension = ".ts"
        # make a test directory if it doesnt already exist
        os.makedirs(os.path.join(
                self.base, self.internal_repo_path, "all_generated/"),
                exist_ok=True
            )
        test_dir = f"test_{fnhash}"

        os.makedirs(os.path.join(
                self.base, self.internal_repo_path, "all_generated/", test_dir), 
                exist_ok=True
            )
        file_contents = []
        for i in range(len(full_tests)):
            imports = self.add_imports_to_file(fnhash)
            full_test_string = full_tests[i]
            # save the test to its own file
            test_file_name = f"{i}{extension}"
            with open(
                os.path.join(
                    self.base,
                    self.internal_repo_path,
                    "all_generated",
                    test_dir,
                    test_file_name
                ),
                "w",
                ) as f:
                # it works far worse without imports (all tests failed bc of viability)
                f.write(imports)
                f.write(full_test_string)
                file_contents.append(imports + "\n" + full_test_string)
            if fnhash in self.all_tests.keys():
                self.all_tests[fnhash].append(full_test_string)
            else:
                self.all_tests[fnhash] = [full_test_string]

        return file_contents


    def evaluate_tests(self, fnhash, full_tests):
        """
        Helper method that assesses the generated unit test
        to see if it's a syntactically correct, and calls
        the focal method being tested, and whether the
        test passes or fails
        """
        pass
    

@dataclass
class Completion:
    completion: str
