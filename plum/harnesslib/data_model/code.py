"""
Data classes for representing code as text and tokens.
"""

from dataclasses import dataclass
from pathlib import Path
from plum.harnesslib.data_model.base import DataModel

from plum.harnesslib.data_model.prompt import SourceFile


@dataclass
class CodeLocation:
    """A location in a file of source code."""

    offset: int
    """The character offset from the start of the file."""

    line: int
    """The line number starting at one."""

    column: int
    """The column number starting at one."""

    @staticmethod
    def from_offset(file: SourceFile, offset: int) -> "CodeLocation":
        """Calculate line and column from code and offset.

        Args:
            file: The file containing the code.
            offset: The offset into the file.

        Returns:
            A CodeLocation object.
        """
        line = 1
        column = offset
        for ln, line_offset in file.line_offsets.items():
            line = ln
            column = (offset - line_offset) + 1
            if line_offset >= offset:
                break

        return CodeLocation(
            offset=offset,
            line=line,
            column=column,
        )

    @staticmethod
    def from_line_column(file: SourceFile, line: int, column: int) -> "CodeLocation":
        """Calculate offset from code, line and column.

        Args:
            file: The file containing the code.
            line: The line number starting at one.
            column: The column number starting at one.

        Returns:
            A CodeLocation object.
        """
        return CodeLocation(
            offset=file.line_offsets[line] + (column - 1),
            line=line,
            column=column,
        )

    def is_valid_for(self, file: SourceFile) -> bool:
        """Check if the location can be used to describe a point in this source file.
        For that, offset and line / column need to match, and be contained in the file.

        Args:
            file: The file containing the code.

        Returns:
            True if the location is valid.
        """
        return (self.offset >= 0 and self.offset <= len(file.source) and
                self.line >= 1 and self.column >= 1 and
                self.offset == file.line_offsets[self.line] + (self.column - 1))


@dataclass
class CodeFragment(DataModel):
    """
    A span of code in a file of source code.

    See also: The :class:`harnesslib.tasks.EvaluateUnitTests` task takes a `CodeFragment` as
    input.
    """

    start: CodeLocation
    """The location of the first character in the code fragment."""

    end: CodeLocation
    """The location of the last character in the code fragment."""

    content: str
    """The full text of the code fragment."""

    relative_path: Path
    """The file containing the code fragment."""

    def __len__(self) -> int:
        return self.end.offset - self.start.offset

    @staticmethod
    def from_offsets(file: SourceFile, start: int, end: int) -> "CodeFragment":
        assert file.relative_path
        return CodeFragment(
            start=CodeLocation.from_offset(file, start),
            end=CodeLocation.from_offset(file, end),
            content=file.source[start:end],
            relative_path=file.relative_path,
        )

    @staticmethod
    def from_line_column(file: SourceFile, start_line: int, start_column: int,
                         end_line: int, end_column: int) -> "CodeFragment":
        assert file.relative_path
        start = CodeLocation.from_line_column(file, start_line, start_column)
        end = CodeLocation.from_line_column(file, end_line, end_column)
        return CodeFragment(
            start=start,
            end=end,
            content=file.source[start.offset:end.offset],
            relative_path=file.relative_path,
        )

    def indentation(self) -> int:
        """
        Returns the indentation of the first non-blank line of the code fragment as a number of
        spaces or tabs.

        If the code fragment is empty, returns 0.
        """
        lines = self.content.splitlines()
        for line in lines:
            if line.strip():
                return len(line) - len(line.lstrip())
        return 0


@dataclass
class CodeBlock(DataModel):
    """A code block extracted from a Code fragment or Function."""
    type: str
    """The type of the code block. This correspondes to a tree-sitter node type name."""

    text: str
    """The text of the code block."""

    height: int
    """The height index of the block in the fragment AST tree."""

    start_byte: int
    """The byte offset of the start of the code block in the fragment AST tree."""

    end_byte: int
    """The byte offset of the end of the code block in the fragment AST tree."""

    is_named: bool
    """Whether the code block is a named treesitter node."""

    child_count: int
    """The number of children of the code block."""

    parent_index: int
    """The index of the parent of the code block in the array serialized fragment AST tree."""

    block_index: int = 0
    """The index of the extracted block in function."""
