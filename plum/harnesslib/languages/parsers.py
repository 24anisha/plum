from abc import ABC, abstractmethod
import os
from pathlib import Path
import queue
from plum.harnesslib.data_model.code import CodeBlock

from tree_sitter import Language, Node, Parser, Tree
from typing import Tuple


class FunctionBodyParser(ABC):
    @abstractmethod
    def parse_body(self, code: str) -> Tuple[str, str]:
        ...


class TreeSitterParserFactory:
    "Returns tree sitter parser for a language"
    root = str(Path(__file__).parent.parent)
    LIBPATH = os.path.join(
        root,
        "external/tree-sitter/build/my-languages.so"
    )

    @staticmethod
    def get_parser(language: str) -> Parser:
        "Get parser for the language"
        parser = Parser()
        if language.lower() == "javascript" or language.lower() == "typescript":
            parser.set_language(
                Language(
                    TreeSitterParserFactory.LIBPATH,
                    "typescript"
                )
            )
            return parser
        elif language.lower() == "python":
            parser.set_language(
                Language(
                    TreeSitterParserFactory.LIBPATH,
                    "python"
                )
            )
        elif language.lower() == "java":
            parser.set_language(
                Language(
                    TreeSitterParserFactory.LIBPATH,
                    "java"
                )
            )

            return parser
        else:
            raise ValueError(f"Unsupported language {language}")


class TreeWalkerState(ABC):
    """This class is used to maintain a state as a
    result of tree traversal. The update method
    takes a node traversed as part of the tree. The
    traverse_children function is used by the walker to
    determine whether it should process the children
    of the given tree or not.

    Args:
        ABC (_type_): _description_
    """

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def update(self, node: Node):
        "Update the state using the current node"
        pass

    @abstractmethod
    def traverse_children(self, node: Node) -> bool:
        "Should the walker process the children"


class TreeSitterWalker:
    @staticmethod
    def walk(parser: Parser, source: bytes, state: TreeWalkerState):
        "Walks the tree of nodes given by tree sitter"
        tree = parser.parse(source)
        q: queue.Queue[Node] = queue.Queue()
        q.put(tree.root_node)
        while q.qsize():
            node = q.get()
            state.update(node)
            if state.traverse_children(node):
                for n in node.children:
                    q.put(n)


def keep_until_unmatched_rbrace(source: str) -> Tuple[str, str]:
    """
    Return the prefix of `source` up to (but not including) the first unmatched closing brace.
    If there are no unmatched closing braces, return the whole source.
    The current implementation is somewhat heuristic; it does not try to recognize braces in
    strings, comments, or regular expressions.
    """
    open_braces = 0
    for i in range(0, len(source)):
        if source[i] == '}':
            if open_braces == 0:
                return source[:i], source[i:]
            open_braces -= 1
        elif source[i] == '{':
            open_braces += 1
    return source, ""


class TreeSitterBlockParser():
    """Parse a code string and return a serialized list of CodeBlock objects
    """

    def __init__(self, parser: Parser):
        self.parser = parser

    def parse_string(self, code_string: str, error_retry: bool = False) -> Node:
        """Return root node of tree for given code string

        Args:
            code_string (str): str representing code
            error_retry (bool, optional): remove last line of codestring and
                retry parsing if root node is error. Defaults to False.

        Returns:
            _type_: _description_
        """
        code_byte: bytes = bytes(code_string, "utf8")
        tree: Tree = self.parser.parse(code_byte)
        cursor = tree.walk()   # type: ignore
        root = cursor.node
        if error_retry:
            error_count = 0
            while (root.type == "ERROR" and root):
                error_count += 1
                # remove last line from code_string and call again
                code_string = code_string[:code_string.rfind('\n')]
                code_byte = bytes(code_string, "utf8")
                tree = self.parser.parse(code_byte)
                cursor = tree.walk()   # type: ignore
                root = cursor.node
        return root

    def walk(self, code_string: str, named_only: bool = False) -> list[CodeBlock]:
        """Return array of blocks for given code bytes

        Args:
            code_string (str): string representing code
            named_only (bool, optional): retry parsing if root node is error. Defaults to False.

        Returns:
            list[dict]: list of discovered blocks
        """
        # convert code string to tree, traverse tree bfs
        code_bytes = bytes(code_string, "utf8")
        root: Node = self.parse_string(code_string)
        queue: list[tuple[Node, int, int]] = [(root, 0, 0)]
        blocks: list[CodeBlock] = []  # list representation of code string
        token_index = 0
        while queue:
            node, height, parent_index = queue.pop()
            if node:
                if named_only and not node.is_named:
                    continue
                if node.type != "module":
                    block_text = code_bytes[node.start_byte: node.end_byte].decode("utf-8")
                    token_index += 1
                    block = CodeBlock(
                        type=node.type,
                        text=block_text,
                        height=height,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        is_named=node.is_named,
                        child_count=node.child_count,
                        parent_index=parent_index
                    )
                    blocks.append(block)
                if node.children:
                    height = height + 1
                    for child in node.children[::-1]:
                        queue.append((child, height, token_index))  # type: ignore
        return blocks

    def extract_blocks(
            self,
            code_string: str,
            max_lines_per_block: int = 10,
            skip_parent_block: bool = True,
            named_only: bool = True) -> list[CodeBlock]:
        """Extract blocks from code string and return list of CodeBlock objects
            Args:
                code_string (str): string representing code
                max_lines_per_block (int, optional): max number of lines per block. Defaults to 10.
                skip_parent_block (bool, optional): skip parent block. Defaults to True.
                named_only (bool, optional): skip unnamed blocks. Defaults to True.
            Returns:
                list[CodeBlock]: list of discovered blocks
        """

        extracted_blocks: list[CodeBlock] = []
        all_blocks: list[CodeBlock] = self.walk(code_string, named_only=named_only)
        block_index: int = 0

        def process_block(block: CodeBlock, block_index: int) -> int:
            block.block_index = block_index
            extracted_blocks.append(block)
            return block_index + 1

        current_depth = 1
        last_expand_point = 1
        for block in all_blocks:
            if block.type == "block" and len(block.text.split("\n")) >= max_lines_per_block:
                last_expand_point = block.height
                current_depth = block.height + 1
                if skip_parent_block:
                    extracted_blocks.pop()
            elif block.height == current_depth and block.is_named:
                block_index = process_block(block, block_index)
            elif block.height < last_expand_point:
                current_depth = block.height
                last_expand_point = block.height
                block_index = process_block(block, block_index)
        return extracted_blocks
