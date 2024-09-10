"""
Tasks for discovering functions in Javascript.
Pulled from harnesslib
"""
import itertools
import logging
import os
from pathlib import Path

from source_parser.tree_sitter import get_language
from tree_sitter import Language as L, Parser

from plum.harnesslib.data_model import ClonedRepoInfo, Function, SourceFile
from plum.harnesslib.languages import Language
from plum.harnesslib.languages.parsers import TreeSitterWalker
from plum.harnesslib.languages.javascript.parsers import JavascriptTreeWalkerState


logger = logging.getLogger('harnesslib')


class JavascriptDiscoverFunctions():
    """Task for discovering the functions in a Javascript repo."""

    def __init__(self, repo_info: ClonedRepoInfo, language: Language = Language.Javascript):
        """Create a new task for discovering functions in a Python repo.

        :param repo_info: The locally cloned repo to process.
        """
        self.repo_info = repo_info

        self.lang = get_language("javascript")
        parser = Parser()
        parser.set_language(self.lang)
        self.parser = parser

        js_extensions = ["*.js", "*.jsx", "*.mjs", "*.cjs"]
        ts_extensions = ["*.ts", "*.tsx"]
        if language not in [Language.Javascript, Language.Typescript]:
            raise ValueError("Only javascript and typescript accepted")

        self._extensions = js_extensions if language == Language.Javascript else ts_extensions
        self._language = language

    def execute(self) -> list[Function]:
        """Runs the task to get javascript function
        bodies for a repo.

        Returns:
            list[JavascriptFunction]: list of functions
        """
        discovered: list[Function] = []
        names = []
        values = []
        loc2glob_exprfn_names = {}
        path2exports = {}
        # parser = TreeSitterParserFactory.get_parser("javascript")
        node_modules = os.path.join(self.repo_info.clone_path, "node_modules")
        generated_tests = os.path.join(self.repo_info.clone_path, "all_generated")
        for file_path in itertools.chain.from_iterable(
                [self.repo_info.clone_path.glob(f"**/{x}") for x in self._extensions]):
            if str(file_path).startswith(node_modules) or str(file_path).startswith(generated_tests):
                continue
            with file_path.open('r') as fin:
                try:
                    contents = fin.read()
                    relative_path = file_path.relative_to(self.repo_info.clone_path)
                    state = JavascriptTreeWalkerState(SourceFile(
                        repo_slug=self.repo_info.slug,
                        relative_path=relative_path,
                        source=contents,
                        language_id=self._language
                    ))
                    TreeSitterWalker.walk(
                        parser=self.parser,
                        source=bytes(contents, "utf8"),
                        state=state
                    )

                    # import pdb
                    # pdb.set_trace()
                    discovered.extend(state.functions())

                    # TODO call query that looks for variable declarator functions
                    # and update name of function accordingly
                    self.handle_expression_functions(contents, loc2glob_exprfn_names)
                    exports = self.discover_module_exports(contents)
                    if exports:
                        path2exports[file_path] = exports
                    

                except UnicodeDecodeError as e:
                    logger.error(e)
                except SyntaxError as e:
                    logger.error(e.msg)
                    return [], {}
        
        function_discovery_metadata = {
            "functions": discovered,
            "expressionfn_names": loc2glob_exprfn_names,
            "path2exports": path2exports
        }
        return function_discovery_metadata
    
    def handle_expression_functions(self, contents, old_to_new_names):
        """
        Parses the code with a query designed to find expression functions. 
        Returns: dict {old_function_name : new_function_name}
        If it's an anonymous expression fn, they are the same
        else, it is the local name mapped to the global name

        LOCALLY NAMED EXPRESSION FUNCTION:
        let multiply = function mul(num1,num2) {
            let product = num1 * num2; 
            return product;
        }
        return {mul : multiply}

        ANONYMOUS EXPRESSION FUNCTION:
        let firstletter = function (string) {
            let first = string.charAt(0);
            return first;
        }
        return {firstletter : firstletter}
        """

        # query for getting expression functions
        query_expressionfn = self.lang.query(
            """
            (variable_declarator 
            name: (identifier) @n
            value: (function) @f
            )
            """)

        code = bytes(contents, "utf-8")
        tree = self.parser.parse(code)

        # parse code to get tree of function name, function body nodes
        function_nodes = query_expressionfn.captures(tree.root_node)
        correct_name = ""

        for node, label in function_nodes:

            # "n" -> name of function (left side of =)
            if label == "n":
                correct_name = code[node.start_byte : node.end_byte].decode()
            
            # "f" -> function body (right side of =)
            elif label == "f":

                # bool that determines whether the current function
                # is locally named (versus anonymous)
                locally_named = False
                for child in node.named_children:
                    # locally named functions have "identifier" children
                    # with the local function name 
                    if child.type == "identifier":
                        old_to_new_names[child.text.decode()] = correct_name
                        locally_named = True
                        break
                # anonymous functions have the correct name as f.name already
                if not locally_named:
                    old_to_new_names[correct_name] = correct_name

        return old_to_new_names

    def discover_module_exports(self, contents):
        """
        Runs a query on the given file to find 
        and return the module.exports string
        """
        # query for getting expression functions
        query_module_exports = self.lang.query(
            """
            (assignment_expression
            left: (member_expression) @m
            right: (object) @e
            )
            """)
        code = bytes(contents, "utf-8")
        tree = self.parser.parse(code)
        is_module_exports = False

        function_nodes = query_module_exports.captures(tree.root_node)
        for node, label in function_nodes:
            # if it is module.exports, then return the next node
            if label == "m":
                is_module_exports = node.text.decode() == "module.exports"
            # return the contents within {}
            elif label == "e" and is_module_exports:
                return node.text.decode()
        # if there is no module.exports in the given file
        return None
