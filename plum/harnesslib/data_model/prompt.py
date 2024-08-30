"""
Data classes for prompts.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from plum.harnesslib.data_model.base import DataModel
from plum.harnesslib.data_model.repo import ClonedRepoInfo
from plum.harnesslib.languages.languages import Language


@dataclass
class SourceFile(DataModel):
    """
    Class to store the content of a file.
    """
    source: str
    "A string containing the text of the program"

    language_id: Language
    "The language the program is written in (lowercase)"

    relative_path: Optional[Path] = None
    "The file path of the document relative to its containing project or folder, if known."

    repo_slug: Optional[str] = None

    def __post_init__(self):
        """Store a mapping from line numbers to character offsets.

            This is used to convert between (line, column) locations and character
            offsets. Line numbers are 1-based.
            """
        self.line_offsets: dict[int, int] = {}
        line_offset = 0
        line = 1
        for source_line in self.source.splitlines(True):
            self.line_offsets[line] = line_offset
            line_offset += len(source_line)
            line += 1
        self.line_offsets[line] = line_offset

    @staticmethod
    def from_repo(repo: ClonedRepoInfo, relative_path: Path) -> "SourceFile":
        with (repo.clone_path / relative_path).open() as file:
            return SourceFile(
                source=file.read(),
                language_id=repo.language,
                relative_path=relative_path,
                repo_slug=repo.slug
            )


@dataclass
class Prompt(DataModel):
    """Represents a prompt."""

    prefix: str
    """The prefix text"""

    suffix: str
    """The suffix text"""

    prefix_length: int
    """The length of the prefix in tokens"""

    suffix_length: int
    """The length of the suffix in tokens"""

    prompt_choices: dict[str, dict[str, str]]
    """Background on the prompt creation"""


class PromptlibPrompt(Prompt):
    """
    The prompt and info as returned by promptlib.

    Implements the Protocol prompt.Prompt
    """

    """TODO: Ingest the choices made during prompt crafting"""

    def __init__(self, prefix: str, suffix: str, prefixLength: int,
                 suffixLength: int, promptChoices: dict[str, dict[str, str]]):
        """Construct a prompt info from json camlCase arguments"""
        super().__init__(prefix, suffix, prefixLength, suffixLength, promptChoices)
