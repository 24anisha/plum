import re
from pathlib import Path
import subprocess
import os 
from source_parser.parsers import JavascriptParser
from source_parser.tree_sitter import get_language
from tree_sitter import Language as L, Parser

from plum.harnesslib.data_model import ClonedRepoInfo
from plum.harnesslib.languages import Language
from plum.utils.function import Function
from plum.utils.logger import Logger


# use this code to iterate through all files in a repo
class JavascriptDiscover():
    def __init__(self,
                 repo_info: ClonedRepoInfo,
                 language: Language,
                 excluded_paths: list[str] = [
                     r'all_generated',
                     r'node_modules',
                     r'export_code_temp'
                 ]):
        """Create a new task for discovering functions in a JS or TS repo.
        :param repo_info: The locally cloned repo to process.
        :param excluded_paths: A list of regexes that match paths to exclude from processing.
        """
        self.repo_info = repo_info
        self._excluded_paths = excluded_paths
        js_extensions = [".js", ".jsx"]
        ts_extensions = [".ts", ".tsx"]
        self.language = language
        self.parser_lang = get_language("javascript")
        parser = Parser()
        # always use the javascript parser bc athena typescript parser doesnt work/exist
        parser.set_language(self.parser_lang)
        self.parser = parser

        self._extensions = js_extensions if language == Language.Javascript else ts_extensions

    def discover(self):
        """
        Iterate through the files in a repo and return a list of the functions
        """

        discovered = []
        rel_path2file_str = {}
        path2exports = {}
        queue = [self.repo_info.clone_path]

        while len(queue) > 0:
            file_path = queue.pop()
            path_to_match = file_path.as_posix().lower()
            if any(re.search(excluded, path_to_match) is not None for excluded in self._excluded_paths):
                continue
            if file_path.is_dir():
                queue.extend(file_path.iterdir())
            elif file_path.is_file() and file_path.suffix in self._extensions:
                methods, relative_path, contents = self.jsts_discover_functions_in_file(file_path)

                if self.language == Language.Javascript:
                    exports = self.discover_module_exports_js(file_path)
                else:
                    # TODO fix for ts (once other ts issues are fixed)
                    exports = self.discover_exports_ts(contents)
                discovered.extend(methods)
                rel_path2file_str[relative_path] = contents
                if exports:
                    path2exports[file_path] = exports

        return {"functions": discovered,
                "rel_path2file_str": rel_path2file_str,
                "path2exports": path2exports}

    # def walk_repository(self, fn: Callable):
    #     queue = [self.repo_info.clone_path]
    #     results = []
    #     while len(queue) > 0:
    #         file_path = queue.pop()
    #         path_to_match = file_path.as_posix().lower()
    #         if any(re.search(excluded, path_to_match) is not None for excluded in self._excluded_paths):
    #             continue
    #         if file_path.is_dir():
    #             queue.extend(file_path.iterdir())
    #         elif file_path.is_file() and file_path.suffix in self._extensions:
    #             results.append(fn())



    # def discover(self, modes: list[str], paths_to_test: list[str] = []):
    #     """
    #     Iterate through the files in a repo and return information collected from the files,
    #     based on what the user wants to discover.
    #     :param modes: list of keywords specifying the type(s) of information to discover. Options are:
    #         - functions: returns a list of functions discovered in the repo
    #         - exports: returns a dictionary mapping relative file paths to the exports in that file
    #         - file_contents: returns a dictionary mapping relative file paths to the contents of that file
    #         - testable_files: returns a list of the files in the repo that can have npm test run on them
    #     :param paths_to_test: a list of paths to files to test. If empty, all files in the repo will be tested.
    #     """
    #     # all of the available ways to use discover 
    #     discovered_methods = []
    #     rel_path2file_str = {}
    #     path2exports = {}
    #     testable_files = []

    #     queue = [self.repo_info.clone_path]

    #     while len(queue) > 0:
    #         file_path = queue.pop()
    #         path_to_match = file_path.as_posix().lower()
    #         if any(re.search(excluded, path_to_match) is not None for excluded in self._excluded_paths):
    #             continue
    #         if file_path.is_dir():
    #             queue.extend(file_path.iterdir())
    #         elif file_path.is_file() and file_path.suffix in self._extensions:

    #             if "functions" in modes:
    #                 methods, relative_path, contents = self.jsts_discover_functions_in_file(file_path)
    #                 discovered_methods.extend(methods)
                
    #             if "exports" in modes:
    #                 if self.language == Language.Javascript:
    #                     exports = self.discover_module_exports_js(file_path)
    #                 else:
    #                     # TODO fix for ts (once other ts issues are fixed)
    #                     exports = self.discover_exports_ts(contents)
    #                 if exports:
    #                     path2exports[file_path] = exports
                
    #             if "file_contents" in modes:
    #                 rel_path2file_str[relative_path] = contents
                
    #             if "testable_files" in modes:
    #                 if (paths_to_test != [] and relative_path in paths_to_test) or paths_to_test == []:

    #                     is_testable = self.is_testable_file(file_path)
    #                     if is_testable:
    #                         testable_files.append(file_path)

    #     return {"functions": discovered_methods,
    #             "rel_path2file_str": rel_path2file_str,
    #             "path2exports": path2exports,
    #             "testable_files": testable_files}

    def get_testable_files(self, test_library, files_to_test=[]):
        """
        Walk through a directory and get a list of all the files for which we can run npm test
        """

        clean_files = []
        queue = [self.repo_info.clone_path]

        while len(queue) > 0:
            file_path = queue.pop()
            path_to_match = file_path.as_posix().lower()
            if any(
                re.search(excluded, path_to_match) is not None
                for excluded in self._excluded_paths
            ):
                continue
            if file_path.is_dir():
                queue.extend(file_path.iterdir())
            elif file_path.is_file() and file_path.suffix in self._extensions:
                relative_path = str(file_path.relative_to(self.repo_info.clone_path))
                if (
                    files_to_test != [] and relative_path not in files_to_test
                ) or "test" in relative_path:
                    continue

                try:
                    if self.is_testable_file(relative_path, test_library):
                        clean_files.append(relative_path)

                except Exception as e:
                    Logger().get_logger().error(f"Error running npm test on {relative_path}: {e}")


        return clean_files


    def is_testable_file(self, relative_path, test_library):
        """
        Given a file path, run npm test on it and return whether it passes or fails.
        :param relative_path: the path of the file to test, relative to the repo root

        """

        try:
            path = Path(self.repo_info.clone_path)
            
            Logger().get_logger().info(self.repo_info.clone_path)
            if test_library == "mocha":
                file_path_to_test = relative_path
                passing_indicator = '"passing" in stdout and "failing" not in stdout and stderr == ""'

            elif test_library == "jest" or not test_library:
                passing_indicator = '"1 passed, 1 total" in stderr and "failed" not in stderr'

                # append a test that is guaranteed to pass before running with jest
                new_file_contents = (
                    open(relative_path, "r").read()
                    + "\n\n"
                    + """
describe('Trivial Sanity Test', () => {
test('trivial (always passes)', () => {
expect(3).toBe(3);
});
});"""
                )
                # change the suffix to .test.js or.test.ts
                relative_path = relative_path.with_suffix(
                    ".test" + relative_path.suffix
                )
                test_relative_path = str(relative_path)
                file_path_to_test = (
                    Path(self.repo_info.clone_path)
                    / test_relative_path
                )

                if not os.path.exists(file_path_to_test):
                    with open(file_path_to_test, "w") as f:
                        f.write(new_file_contents)
                else:
                    return False

            output = subprocess.run(
                ["npm", "test", file_path_to_test],
                cwd=path,
                timeout=30,
                capture_output=True,
            )
            
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            Logger().get_logger().info(stdout)
            Logger().get_logger().warning(stderr)

            if file_path_to_test != relative_path:
                os.remove(file_path_to_test)

            if eval(passing_indicator):
                return True

            return False

        except Exception as e:
            Logger().get_logger().error(f"Error running npm test on {relative_path}: {e}")


    def jsts_discover_functions_in_file(self, file_path):
        """
        Returns all functions/methods found in a file with the information:
        all keys from schema + 'relative_path', 'class': {'docstring', 'definition', 'name',
                                                'byte_span', 'original_string', 'start', 'end'}
        """
        relative_path = str(file_path.relative_to(self.repo_info.clone_path))
        contents = open(file_path).read()

        methods = []
        try:
            pp = JavascriptParser(contents)

            for function in pp.schema['methods']:
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
            Logger().get_logger().exception(e)
            Logger().get_logger().debug(self.repo_info.clone_path)
            Logger().get_logger().debug(relative_path)

        return methods, relative_path, contents


    def discover_module_exports_js(self, file_path):
        """
        Uses ts-morph and a subprocess call to get the exports
        from a given file
        """

        # DONE 1: pass full path, not contents
        # DONE 2: write function that writes file with set structure (but different file path)
        # to the focal repo
        exports = set({})
        export_file_path = write_export_file(self.repo_info, file_path)
        # Logger().get_logger().info(export_file_path)

        # DONE 3: use subprocess to run node filename.js and save stdout
        output = subprocess.run(["node", export_file_path], capture_output=True)
        # TODO MAKE SURE IT COLLECTS ALL CALLS TO CONSOLE.LOG IN STDOUT
        stdout = output.stdout.decode("utf-8")
        exports.update(stdout.split(",\n"))
        stderr = output.stderr.decode("utf-8")

        contents = open(file_path).read()
        query_module_exports = self.parser_lang.query(
            """
            (assignment_expression
            left: (member_expression) @m
            right: (identifier) @e
            )
            """)
        code = bytes(contents, "utf-8")
        tree = self.parser.parse(code)
        is_module_exports = False

        function_nodes = query_module_exports.captures(tree.root_node)
        for node, label in function_nodes:

            # if it is module.exports, then return the next node
            if label == "m":
                is_module_exports = "module.exports" in node.text.decode()
            # return the contents within {}
            elif label == "e" and is_module_exports:
                exports.add(node.text.decode())
        # if there is no module.exports in the given file
        exports = [e for e in exports if e != ""]
        if len(exports) == 0:
            return None
        else:
            return " { " + ",\n".join(exports) + " }"

    def discover_exports_ts(self, contents):
        """
        Runs a query on the given file to find 
        and return the module.exports string
        """
        # query for getting expression functions
        query_exports = self.parser_lang.query(
            """
            (export_statement
                (export_clause) @c
            )
            """)
        code = bytes(contents, "utf-8")
        tree = self.parser.parse(code)
        is_module_exports = False

        function_nodes = query_exports.captures(tree.root_node)
        for node, label in function_nodes:
            # if it is module.exports, then return the next node
            if label == "c":
                return node.text.decode()
        # if there is no module.exports in the given file
        return None

def write_export_file(repo_info, file_path):
    # template string to write (and re-write) for each file in the focal repo
    template = """
        const { ExportedDeclarations, Project } = require("ts-morph")

        const project =  new Project({
            compilerOptions: { allowJs: true }
        });
        const sourceFile = project.addSourceFileAtPath("%FILE_PATH_HERE%")
        const diagnostics = project.getPreEmitDiagnostics()

        const exportDeclarations = sourceFile.getExportedDeclarations();
        for (const [name, declarations] of exportDeclarations)
            console.log(`${name},`);
        """
    template = template.replace("%FILE_PATH_HERE%", str(file_path))
    export_js_path = Path(repo_info.clone_path) / "export_code_TEMP.js"
    with open(export_js_path, 'w') as f:
        f.write(template)
    
    return export_js_path


