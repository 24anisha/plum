from typing import List
import re


from plum.actions.csharp._log_types import (
    ErrorType,
    MSBuildError,
    NuGetError,
    NETSDKError
)


class BuildLog:
    """Structured representation of an MSBuild log."""
    BASE_ERROR_URL = "https://learn.microsoft.com/en-us/visualstudio/msbuild/errors/"
    NUGET_ERROR_URL = "https://learn.microsoft.com/en-us/nuget/reference/errors-and-warnings/"
    NETSDK_ERROR_URL = "https://learn.microsoft.com/en-us/dotnet/core/tools/sdk-errors/"

    _msbuild_regex = re.compile(r'MSBUILD : error (MSB\d+): (.+)')
    _nuget_regex = re.compile(r'(.+\.csproj) : error (NU\d+): (.+) \[(.+\.sln)\]')
    _netsdk_regex = re.compile(r'(\/.+)\((\d+),(\d+)\): (error) (NETSDK\d+): (.+) \[(.+)\]')

    def __init__(self, version: str, errors: List[ErrorType]):
        self.version = version
        self.errors = errors

    @staticmethod
    def parse(log_text: str):
        version = BuildLog._extract_version(log_text)
        errors = BuildLog._extract_errors(log_text)
        return BuildLog(version, errors)

    @staticmethod
    def _extract_version(log_text: str):
        match = re.search(r'MSBuild version (\d+\.\d+\.\d+\+\d+)', log_text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_errors(log_text: str) -> List[ErrorType]:
        errors = []

        # The log may or may not have "Build FAILED." in the middle; but if it does, we use the part after it.
        failed_section = log_text.split("Build FAILED.\n")[-1]

        # Match MSBuild errors
        msbuild_errors = BuildLog._msbuild_regex.findall(failed_section)
        for error in msbuild_errors:
            errors.append(
                MSBuildError(
                    code=error[0],
                    message=error[1],
                    url=BuildLog.BASE_ERROR_URL + error[0].lower()
                )
            )

        # Match NuGet errors
        nuget_errors = BuildLog._nuget_regex.findall(failed_section)
        for error in nuget_errors:
            errors.append(
                NuGetError(
                    code=error[1],
                    message=error[2],
                    url=BuildLog.NUGET_ERROR_URL + error[1].lower(),
                    project_file=error[0],
                    solution_file=error[3]
                )
            )

        # Match NETSDK errors
        netsdk_issues = BuildLog._netsdk_regex.findall(failed_section)
        for issue in netsdk_issues:
            file_path, line_number, char_number, _, code, message, project_file = issue
            errors.append(
                NETSDKError(
                    code=code,
                    message=message,
                    url=BuildLog.NETSDK_ERROR_URL + code.lower(),
                    file_path=file_path,
                    line_number=int(line_number),
                    char_number=int(char_number),
                    project_file=project_file
                )
            )
        return errors

    def __str__(self):
        output = [f"MSBuild Version: {self.version}"]
        for error in self.errors:
            output.append(f"Project File: {error.project_file}" if error.project_file else "")
            output.append(f"Solution File: {error.solution_file}" if error.solution_file else "")
            output.append(f"Error Code: {error.code}")
            output.append(f"Error Message: {error.message}")
            output.append(f"More Info: {error.url}")
        return "\n".join(output)
