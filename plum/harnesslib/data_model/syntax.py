"""Data classes for representing the syntactic structure of code."""


from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from plum.harnesslib.data_model.base import DataModel
from plum.harnesslib.data_model.code import CodeFragment
from plum.harnesslib.languages import Language


@dataclass
class Function(DataModel):
    """Class to store the parsed content of a function."""

    name: str
    "The name of the function"

    language_id: Language
    "The language of the function."

    relative_path: Path
    "The relative path to the file containing the function."

    header: CodeFragment
    "Only the function header, including the name and arguments."

    documentation: Optional[CodeFragment]
    "Only the function docstring. Empty string if not present"

    body: CodeFragment
    "The body of the function including opening and closing braces if applicable."

    repo_slug: Optional[str]
    "The repo slug formatted as owner/repo."
