"""Basic definitions around language support."""

from enum import Enum


class Language(str, Enum):
    """
    Enum for supported languages.

    The string representation of each element is the "languageId" as used by e.g. promptlib.
    """

    Python = "python"
    Javascript = "javascript"
    Typescript = "typescript"
    Java = "java"
    Csharp = "csharp"
    Cpp= "cpp"

    Unknown = "unknown"
