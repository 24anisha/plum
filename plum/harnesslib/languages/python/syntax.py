"""Tasks for discovering functions in Python."""

import ast
import re
import logging
from pathlib import Path

from plum.harnesslib.data_model import ClonedRepoInfo, CodeLocation, CodeFragment, Function, SourceFile
from plum.harnesslib.languages import Language
from plum.harnesslib.tasks.syntax import DiscoverFunctions


logger = logging.getLogger('harnesslib')


class DiscoveredFunctionParser(ast.NodeVisitor):
    """
    Tree walker that processes every function definition.
    Usually you don't want to call this directly. Instead, use either `PythonDiscoverFunctions` or
    `python_discover_functions_in_str`.
    """

    def __init__(self, file: SourceFile):
        """Create a new parser give a file path and the source code.
        :param relative_path: The relative path to the file that contains the function.
        :param source_code: The source code of the function including the declaration and docstring.
        """
        super().__init__()
        self._file = file
        self.functions: list[Function] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Process a function definition node.
        :param node: The function definition AST node.
        """
        assert self._file.relative_path
        # start scanning at the beginning of the body
        assert node.end_lineno
        assert node.end_col_offset

        header_start = CodeLocation.from_line_column(self._file, node.lineno, node.col_offset + 1)
        header_end = CodeLocation.from_line_column(
            self._file, node.end_lineno, node.end_col_offset + 1)

        # By default, the docstring is the first line of the function
        body_start = CodeLocation.from_line_column(
            self._file, node.lineno + 1, 0)

        # Look for docstring at the beginning of the function
        docstring_start = None
        docstring_end = None
        if node.body:
            if isinstance(node.body[0], ast.Expr) and \
                    isinstance(node.body[0].value, ast.Constant):
                docstring_start = CodeLocation.from_line_column(self._file, node.body[0].lineno, 1)
                header_end = docstring_start
                if len(node.body) > 1:
                    body_start = CodeLocation.from_line_column(self._file, node.body[1].lineno, 1)
                    docstring_end = body_start
                else:
                    body_start = None
                    body_end = None
            else:
                body_start = CodeLocation.from_line_column(self._file, node.body[0].lineno, 1)
                header_end = body_start

        body_end = CodeLocation.from_line_column(
            self._file, node.end_lineno + 1, 1)

        if body_start and body_end:
            self.functions.append(
                Function(
                    name=node.name,
                    language_id=Language.Python,
                    relative_path=self._file.relative_path,
                    header=CodeFragment(
                        start=header_start,
                        end=header_end,
                        content=self._file.source[header_start.offset: header_end.offset],
                        relative_path=self._file.relative_path),
                    documentation=CodeFragment(
                        start=docstring_start,
                        end=docstring_end,
                        content=self._file.source[docstring_start.offset: docstring_end.offset],
                        relative_path=self._file.relative_path)
                    if docstring_start and docstring_end else None,
                    body=CodeFragment(
                        start=body_start,
                        end=body_end,
                        content=self._file.source[body_start.offset: body_end.offset],
                        relative_path=self._file.relative_path),
                    repo_slug=self._file.repo_slug))

        self.generic_visit(node)

        self.generic_visit(node)


class PythonDiscoverFunctions(DiscoverFunctions):
    """Task for discovering the functions in a Python repo."""

    def __init__(self,
                 repo_info: ClonedRepoInfo,
                 excluded_paths: list[str] = [
                     r'all_generated',
                     r'lib/site-packages$',
                     r'.venv$',
                     r'lib/python[0-9\.]+/site-packages$']):
        """Create a new task for discovering functions in a Python repo.
        :param repo_info: The locally cloned repo to process.
        :param excluded_paths: A list of regexes that match paths to exclude from processing.
        """
        super().__init__(repo_info)
        self._excluded_paths = excluded_paths

    def execute(self) -> list[Function]:
        discovered: list[Function] = []
        queue: list[Path] = [self.repo_info.clone_path]

        while len(queue) > 0:
            file_path = queue.pop()
            path_to_match = file_path.as_posix().lower()
            if any(re.search(excluded, path_to_match) is not None
                   for excluded in self._excluded_paths):
                continue
            if file_path.is_dir():
                queue.extend(file_path.iterdir())
            elif file_path.is_file() and file_path.suffix == '.py':
                discovered.extend(python_discover_functions_in_file(file_path, self.repo_info))

        return discovered


def python_discover_functions_in_file(file_path: Path, repo_info: ClonedRepoInfo) -> list[Function]:
    """Discover the functions in a Python source file."""
    with file_path.open('r') as fin:
        try:
            relative_path = file_path.relative_to(repo_info.clone_path)
            source_text = fin.read()
            tree = ast.parse(source_text)
            parser = DiscoveredFunctionParser(SourceFile(
                language_id=Language.Python,
                relative_path=relative_path,
                repo_slug=repo_info.slug,
                source=source_text))
            parser.visit(tree)
            return parser.functions
        except UnicodeDecodeError as e:
            logger.error(e)
        except SyntaxError as e:
            logger.error(e.msg)
    return []


def python_discover_functions_in_str(source: str) -> list[Function]:
    """Discover the functions in a Python source string.
    :param source: The source code to parse.
    :return: The discovered functions.
    """
    tree = ast.parse(source)
    parser = DiscoveredFunctionParser(SourceFile(
        language_id=Language.Python,
        relative_path=Path("from_string"),
        repo_slug="",
        source=source))
    parser.visit(tree)
    return parser.functions
