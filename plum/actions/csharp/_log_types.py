from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class ErrorBase():
    """Immutable container for MSBuild error information."""
    code: str
    """Error code, e.g. MSB1011; NU1301; NETSDK1045."""

    message: str
    """Description of the error."""

    url: str
    """
    Official documentation URL for the error.
    Note that not all errors have documentation, and this URL may not be functional.
    """

@dataclass(frozen=True)
class MSBuildError(ErrorBase):
    """Errors from Visual Studio's MSBuild itself. Error code MSBxxxx."""
    # The properties of this class are existent in all error types.
    pass

@dataclass(frozen=True)
class NuGetError(ErrorBase):
    """Errors from the NuGet package manager. Error code NUxxxx."""
    project_file: str
    """The .csproj or .vbproj file that the error occurred in."""

    solution_file: str
    "The .sln file that the error occurred in."

@dataclass(frozen=True)
class NETSDKError(ErrorBase):
    """Errors from the .NET SDK. Error code NETSDKxxxx."""
    file_path: str
    """The file path that the error occurred in."""

    line_number: int
    """The line number that the error occurred on."""

    char_number: int
    """The character number that the error occurred on."""

    project_file: str
    """The .csproj or .vbproj file that the error occurred in."""

ErrorType = Union[MSBuildError, NuGetError, NETSDKError]
