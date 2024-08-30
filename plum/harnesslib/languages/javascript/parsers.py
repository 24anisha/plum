"""Classes for parsing javascript code."""
import re
from typing import Optional, Tuple

from tree_sitter import Node

from plum.harnesslib.data_model import CodeFragment, Function, SourceFile
from plum.harnesslib.languages.parsers import keep_until_unmatched_rbrace, FunctionBodyParser, \
    TreeWalkerState


class JavascriptFunctionBodyParser(FunctionBodyParser):
    """Parses a javascript function's body."""

    def parse_body(self, code: str) -> Tuple[str, str]:
        """
        If `source` starts with an opening curly brace, return the prefix up to and including the
        closing curly brace. Otherwise, return "{}".
        """
        m = re.match(r"\s*{", code)
        if not m:
            return "{}", ""
        body, remaining = keep_until_unmatched_rbrace(code[m.end():])
        return "{" + body + "}", remaining


class JavascriptTreeWalkerState(TreeWalkerState):
    """TreeWalkerState for javascript."""

    FUNCTION_TYPES = set([
        "function_declaration",
        "generator_function_declaration",
        "arrow_function",
        "function",
        "generator_function",
        "method_definition"
    ])

    def __init__(self, file: SourceFile) -> None:
        "Create a tree walker state that contains the discovered functions"
        super().__init__()
        self._file = file
        self._functions: list[Function] = []
        self._block_comment_re = re.compile(r"^/\*.*\*/$", re.DOTALL)
        self._line_comment_re = re.compile(r"^//.*$")
        self._byte_to_char_offset_map = self._get_byte_char_offset_map(file.source)

    def _get_docstring(self, node: Node, allow_multi_line: bool = True) -> Tuple[int, int]:
        "Get doc start and doc end for a fn node"
        # In js, doc string for a function is the comments preceding
        # function def
        prev = node.prev_sibling
        if prev and prev.type == "comment":
            text = prev.text
            if allow_multi_line and self._block_comment_re.match(text.decode("utf8")):
                return prev.start_byte, prev.end_byte
            elif self._line_comment_re.match(text.decode("utf8")):
                # for single line comments, we also want to
                # take preceding comments
                start, _ = self._get_docstring(prev, False)
                return start, prev.end_byte
        else:
            # check if parent falls into any of following buckets
            # if it does, lets look at doc for parents
            if node.parent and node.parent.type in [
                    "assignment_expression",
                    "variable_declarator",
                    "expression_statement",
                    "variable_declaration",
                    "lexical_declaration",
                    "export_statement"]:
                return self._get_docstring(node.parent, allow_multi_line)

        # if we are here, we dont have a doc comment
        return node.start_byte, node.start_byte

    def _get_byte_char_offset_map(self, s: str) -> dict[int, int]:
        "Returns map from byte to char offsets"
        offset_map: dict[int, int] = {}
        offset_map[0] = 0
        prev_offset = 0

        for i, c in enumerate(s):
            curr_offset = prev_offset + len(bytes(c, "utf8"))
            # assign prev char to all byte positions in between
            for j in range(prev_offset + 1, curr_offset):
                offset_map[j] = i

            offset_map[curr_offset] = i + 1

            prev_offset = curr_offset

        return offset_map

    def _get_named_children(self, node: Node) -> list[Node]:
        "Get named children for a node"
        return [n for n in node.children if n.is_named]

    def _get_child_with_type(self, node: Node, type: str) -> Optional[Node]:
        "Gets first child with the given type"
        child = None
        for c in node.children:
            if c.type == type:
                child = c

        return child

    def _get_fn_name(self, node: Node) -> str:
        "Get name of the function. Logic copied from legacy harness js"

        identifier_child = self._get_child_with_type(node, "identifier")
        prop_id_child = self._get_child_with_type(node, "property_identifier")
        if identifier_child:
            return identifier_child.text.decode("utf8")
        elif prop_id_child:
            return prop_id_child.text.decode("utf8")
        elif node.parent:
            parent_named_children = self._get_named_children(node.parent)
            if node.parent.type == "variable_declarator" and len(parent_named_children) >= 2 and \
                    node == parent_named_children[1]:
                # var f = function() {...}
                return parent_named_children[0].text.decode("utf8")
            elif node.parent.type == "assignment_expression" and \
                    len(parent_named_children) >= 2 and node == parent_named_children[1]:
                first_child = parent_named_children[0]
                if first_child.type == "identifier":
                    return first_child.text.decode("utf8")
                else:
                    first_child_named_children = self._get_named_children(first_child)
                    if first_child.type == "member_expression" and \
                            len(first_child_named_children) >= 2:
                        prop = first_child_named_children[1]
                        if prop.type == "property_identifier" \
                                and prop.text.decode("utf8") != "default" \
                                and prop.text.decode("utf8") != "exports":
                            return prop.text.decode("utf8")

                return self._get_fn_name(node.parent)

        return "<anonymous>"

    def functions(self) -> list[Function]:
        "Return the discovered functions"
        return self._functions

    def traverse_children(self, node: Node) -> bool:
        "Return boolean indicating whether to traverse children"

        return node.type not in JavascriptTreeWalkerState.FUNCTION_TYPES and \
            node.named_child_count > 0

    def update(self, node: Node):
        "Update state given a node"
        assert self._file.relative_path
        if node.child_count and node.type in JavascriptTreeWalkerState.FUNCTION_TYPES:
            doc_start, doc_end = self._get_docstring(node)
            named_children = self._get_named_children(node)

            body_start = self._byte_to_char_offset_map[named_children[-1].start_byte]
            body_end = self._byte_to_char_offset_map[node.end_byte]

            signature_start = self._byte_to_char_offset_map[node.start_byte]
            signature_end = body_start

            documentation_start = self._byte_to_char_offset_map[doc_start]
            documentation_end = self._byte_to_char_offset_map[doc_end]

            self._functions.append(Function(
                name=self._get_fn_name(node),
                relative_path=self._file.relative_path,
                language_id=self._file.language_id,
                header=CodeFragment.from_offsets(
                    file=self._file,
                    start=signature_start,
                    end=signature_end),
                documentation=CodeFragment.from_offsets(
                    file=self._file,
                    start=documentation_start,
                    end=documentation_end),
                body=CodeFragment.from_offsets(
                    file=self._file,
                    start=body_start,
                    end=body_end),
                repo_slug=self._file.repo_slug))
