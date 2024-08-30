import re
from pathlib import Path

from source_parser.parsers import PythonParser

from plum.harnesslib.data_model import ClonedRepoInfo
from plum.utils.function import Function
from plum.utils.logger import Logger


# use this code to iterate through all files in a python repo
class PythonDiscover():
    def __init__(self,
                 repo_info: ClonedRepoInfo,
                 excluded_paths: list[str] = [
                     r'all_generated',
                     r'lib/site-packages$',
                     r'.venv$',
                     r'lib/python[0-9\.]+/site-packages$']):
        """Create a new task for discovering functions in a Python repo.
        :param repo_info: The locally cloned repo to process.
        :param repo_path: The path to the locally cloned repo to process.
        :param excluded_paths: A list of regexes that match paths to exclude from processing.
        """
        self.repo_info = repo_info
        self.repo_path = self.repo_info.clone_path
        self._excluded_paths = excluded_paths

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
            elif file_path.is_file() and file_path.suffix == '.py':
                methods, relative_path, contents = self.python_discover_functions_in_file(file_path)
                discovered.extend(methods)
                rel_path2file_str[relative_path] = contents
        
        return {"functions": discovered,
                "rel_path2file_str": rel_path2file_str,
                "path2exports": None}

    def hash(self, row):
        return row.name + "--" + str(row.start_line) + "--" +row.relative_path.replace("/", "--").replace(".py", "")


    def get_import(self, row):
        definition = row["class"]["definition"]
        if definition:
            if "(" in definition:
                name = definition.split("(")[0].replace("class ", "")
            elif definition.strip()[-1] == ":":
                name = definition.replace("class ", "").replace(":", "")
            else:
                RaiseException
        else:
            name = row["name"]
        return f'from {row["relative_path"].replace("/", ".")[:-3]} import {name}'



    def python_discover_functions_in_file(self, file_path):
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
            pp = PythonParser(contents)
        except Exception as e:
            Logger().get_logger().error(f"Error parsing {relative_path}: {e}")
            return [], relative_path, contents

        imports = "\n".join(line for line in pp.schema["contexts"] if "import" in line)
        for function in pp.schema['methods']:
            function_obj = {}
            function_obj = function
            function_obj['relative_path'] = relative_path
            function_obj['imports'] = imports
            function_obj['class'] = {
                'docstring': None,
                'definition': None,
                'name': None,
                'byte_span': None,
                'original_string': None,
                'start_point': None,
                'end_point': None
            }
            function_obj['import_line'] = self.get_import(function_obj)
            function_object = Function(function_obj)
            methods.append(function_object)

        for class_info in pp.schema['classes']:
            for method in class_info['methods']:
                function_obj = {}
                function_obj = method
                function_obj['relative_path'] = relative_path
                function_obj['imports'] = imports
                function_obj['class'] = {
                    'docstring': class_info['class_docstring'],
                    'definition': class_info['definition'],
                    'name': class_info['name'],
                    'byte_span': class_info['byte_span'],
                    'original_string': class_info['original_string'],
                    'start_point': class_info['start_point'],
                    'end_point': class_info['end_point']
                }
                function_obj['import_line'] = self.get_import(function_obj)
                function_object = Function(function_obj)

                methods.append(function_object)
        

        return methods, relative_path, contents

        # use source parser to get all the function information (in classes or not)
        # add the relative path (aka file_path) to each method it finds, and return the list of methods
        # add any class information that is saved
        # throughout the plum code, find all the places function is used
            # obj = {...}
            # hash2function
            # etc
            # and replace those calls with values from the found methods
        pass
