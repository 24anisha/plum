"""
Utilities for parsing each file in a repository
"""

import logging
from pathlib import Path
import subprocess
import os

from plum.harnesslib.languages import Language
from source_parser.parsers import (
    JavascriptParser,
    PythonParser,
    CSharpParser,
    JavaParser,
    CppParser
)
from plum.utils.function import Function
from plum.utils.logger import Logger



def get_functions_from_file(repo, file_path):
    """
    Passable into walk_repository to get all the functions in a given file
    :param file_path: Path to the file to parse
    :return: List of Function objects from functions in the file
    """
    relative_path = str(file_path.relative_to(repo.repo_root))
    contents = open(file_path).read()

    methods = []
    try:
        if repo.language in (Language.Javascript, Language.Typescript):
            fn_parser = JavascriptParser(contents)
        elif repo.language == Language.Python:
            fn_parser = PythonParser(contents)
        elif repo.language == Language.Java:
            fn_parser = JavaParser(contents)
        elif repo.language == Language.Csharp:
            fn_parser = CSharpParser(contents)
        elif repo.language == Language.Cpp:
            fn_parser = CppParser(contents)
        else:
            Logger().get_logger().error(
                "This language is not yet handled",
                extra={
                    "language": repo.language.value
                })

        for function in fn_parser.schema['methods']:
            function_obj = function
            function_obj['relative_path'] = relative_path
            function_obj['class'] = {
                'docstring': None,
                'definition': None,
                'name': None,
                'byte_span': None,
                'original_string': None,
                'start_point': None,
                'end_point': None
            }
            function_object = Function(function_obj)
            methods.append(function_object)

        for class_info in fn_parser.schema['classes']:
            for method in class_info['methods']:
                function_obj = method
                function_obj['relative_path'] = relative_path
                function_obj['class'] = {
                    'docstring': class_info['class_docstring'],
                    'definition': f"class {class_info['name']} " + "{",
                    'name': class_info['name'],
                    'byte_span': class_info['byte_span'],
                    'original_string': class_info['original_string'],
                    'start_point': class_info['start_point'],
                    'end_point': class_info['end_point']
                }
                function_object = Function(function_obj)

                methods.append(function_object)
    except Exception as e:
        Logger().get_logger().error(f"Could not parse file {repo.base}/{relative_path}: {e}")

    return methods


def is_testable_file(repo, file_path):
    """
    Function callable with walk_repository to determine 
    if a file is testable with either the mocha or jest testing library
    :param file_path: the absolute path to the file to be tested
    :return: True if the file is testable, False otherwise
    """

    is_testable = False
    relative_path = str(file_path.relative_to(repo.base / repo.internal_repo_path))

    try:
        path = (
            Path(repo.base)
            / repo.internal_repo_path
        )
        if repo.test_library == "mocha":
            output = subprocess.run(
                ["npm", "test", relative_path],
                cwd=path,
                timeout=30,
                capture_output=True,
            )
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")

            if (
                "passing" in stdout
                and "failing" not in stdout
                and stderr == ""
            ):
                is_testable = True

        elif repo.test_library == "jest" or not repo.test_library:
            new_file_contents = (
                open(file_path, "r").read()
                + "\n\n"
                + """
describe('Trivial Sanity Test', () => {
test('trivial (always passes)', () => {
expect(3).toBe(3);
});
});"""
            )
            relative_path_as_path = Path(relative_path)
            relative_path_as_path = relative_path_as_path.with_suffix(
                ".test" + relative_path_as_path.suffix
            )
            test_relative_path = str(relative_path_as_path)
            new_file_path = (
                Path(repo.base)
                / repo.internal_repo_path
                / test_relative_path
            )

            if not os.path.exists(new_file_path):
                with open(new_file_path, "w") as f:
                    f.write(new_file_contents)
            else:
                # if the file already, exists, do not override it. Instead, return an empty list, because this file is not testable
                return []

            output = subprocess.run(
                ["npm", "test", test_relative_path],
                cwd=path,
                timeout=30,
                capture_output=True,
            )
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            os.remove(new_file_path)

            if "1 passed, 1 total" in stderr and "failed" not in stderr:
                is_testable = True

    except Exception as e:
        Logger().get_logger().error(f"Error running npm test on {relative_path}: {e}")

    if is_testable:
        return [file_path]
    else:
        return []
