import re
from pathlib import Path

from source_parser.parsers import JavaParser

from plum.harnesslib.data_model import ClonedRepoInfo
from plum.utils.function import Function
from plum.utils.logger import Logger


# use this code to iterate through all files in a Java repo
class JavaDiscover():
    def __init__(self,
                 repo_info: ClonedRepoInfo):
        """Create a new task for discovering functions in a Python repo.
        :param repo_info: The locally cloned repo to process.
        :param repo_path: The path to the locally cloned repo to process.
        :param excluded_paths: A list of regexes that match paths to exclude from processing.
        """
        self.repo_info = repo_info
        self.repo_path = self.repo_info.clone_path
        self._excluded_paths = []

    def discover(self):
        discovered = []
        rel_path2file_str = {}
        queue = [self.repo_info.clone_path]

        while len(queue) > 0:

            file_path = queue.pop()
            path_to_match = file_path.as_posix().lower()
            if any(re.search(excluded, path_to_match) is not None
                    for excluded in self._excluded_paths):
                continue
            if file_path.is_dir():
                queue.extend(file_path.iterdir())
            elif file_path.is_file() and file_path.suffix == '.java':
                methods, relative_path, contents = self.java_discover_functions_in_file(file_path)
                discovered.extend(methods)
                rel_path2file_str[relative_path] = contents

        return {"functions": discovered,
                "rel_path2file_str": rel_path2file_str
                }


    def java_discover_functions_in_file(self, file_path):
        """
        Returns all functions/methods found in a file with the information:
        all keys from schema + 'relative_path', 'class': {'docstring', 'definition', 'name',
                                                'byte_span', 'original_string', 'start', 'end'}
        """
        relative_path = str(file_path.relative_to(self.repo_info.clone_path))
        contents = open(file_path).read()
        if contents.strip() == '':
            return [], relative_path, contents

        methods = []
        try:
            pp = JavaParser(contents)
        except Exception as e:
            Logger().get_logger().error(f"Error parsing {relative_path}: {e}")
            return [], relative_path, contents

        for function in pp.schema['methods']:
            function_obj = {}
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

        for class_info in pp.schema['classes']:
            for method in class_info['methods']:
                function_obj = {}
                function_obj = method
                function_obj['relative_path'] = relative_path
                function_obj['class'] = {
                    'docstring': class_info['class_docstring'],
                    'definition': class_info['definition'],
                    'name': class_info['name'],
                    'byte_span': class_info['byte_span'],
                    'original_string': class_info['original_string'],
                    'start_point': class_info['start_point'],
                    'end_point': class_info['end_point']
                }
                function_object = Function(function_obj)

                methods.append(function_object)


        return methods, relative_path, contents
