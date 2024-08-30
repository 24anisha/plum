import pytest

from plum.actions.csharp._ms_build_log_parser import BuildLog
from plum.actions.csharp._log_types import (
    MSBuildError,
    NuGetError,
    NETSDKError
)

def test_msbuild_log_parser():
    log_text = """MSBuild version 17.3.2+561848881 for .NET
MSBUILD : error MSB1011: Specify which project or solution file to use because this folder contains more than one project or solution file.
"""

    expected_version = "17.3.2+561848881"
    expected_errors = [
        MSBuildError(
            code='MSB1011',
            message='Specify which project or solution file to use because this folder contains more than one project or solution file.',
            url='https://learn.microsoft.com/en-us/visualstudio/msbuild/errors/msb1011'
        )
    ]

    parser = BuildLog.parse(log_text)

    assert parser.version == expected_version, "Version mismatch"
    assert parser.errors == expected_errors, "Errors mismatch"

def test_nuget_errors():
    log_text = """MSBuild version 17.3.2+561848881 for .NET
  Determining projects to restore...
/datadisk/DeepMergeCore/DeepMergeCoreResearchTests/DeepMergeCoreResearchTests.csproj : error NU1301: Unable to load the service index for source https://devdiv.pkgs.visualstudio.com/_packaging/IntelliCode/nuget/v3/index.json. [/datadisk/DeepMergeCore/DeepMergeCore.sln]
/datadisk/DeepMergeCore/GitUtil/GitUtil.csproj : error NU1301: Unable to load the service index for source https://devdiv.pkgs.visualstudio.com/_packaging/IntelliCode/nuget/v3/index.json. [/datadisk/DeepMergeCore/DeepMergeCore.sln]

Build FAILED.

/datadisk/DeepMergeCore/DeepMergeCoreResearchTests/DeepMergeCoreResearchTests.csproj : error NU1301: Unable to load the service index for source https://devdiv.pkgs.visualstudio.com/_packaging/IntelliCode/nuget/v3/index.json. [/datadisk/DeepMergeCore/DeepMergeCore.sln]
/datadisk/DeepMergeCore/GitUtil/GitUtil.csproj : error NU1301: Unable to load the service index for source https://devdiv.pkgs.visualstudio.com/_packaging/IntelliCode/nuget/v3/index.json. [/datadisk/DeepMergeCore/DeepMergeCore.sln]
    0 Warning(s)
    2 Error(s)

Time Elapsed 00:00:33.26
"""

    expected_version = "17.3.2+561848881"
    expected_errors = [
        NuGetError(
            code='NU1301',
            message='Unable to load the service index for source https://devdiv.pkgs.visualstudio.com/_packaging/IntelliCode/nuget/v3/index.json.',
            url='https://learn.microsoft.com/en-us/nuget/reference/errors-and-warnings/nu1301',
            project_file='/datadisk/DeepMergeCore/DeepMergeCoreResearchTests/DeepMergeCoreResearchTests.csproj',
            solution_file='/datadisk/DeepMergeCore/DeepMergeCore.sln'
        ),
        NuGetError(
            code='NU1301',
            message='Unable to load the service index for source https://devdiv.pkgs.visualstudio.com/_packaging/IntelliCode/nuget/v3/index.json.',
            url='https://learn.microsoft.com/en-us/nuget/reference/errors-and-warnings/nu1301',
            project_file='/datadisk/DeepMergeCore/GitUtil/GitUtil.csproj',
            solution_file='/datadisk/DeepMergeCore/DeepMergeCore.sln'
        )
    ]

    parser = BuildLog.parse(log_text)

    assert parser.version == expected_version, "Version mismatch"
    assert parser.errors == expected_errors, "Errors mismatch"

def test_netsdk_warn_and_errors():
    """For now, we only grab errors and ignore warnings."""
    log_text = """MSBuild version 17.3.2+561848881 for .NET
  Determining projects to restore...
/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.EolTargetFrameworks.targets(29,5): warning NETSDK1138: The target framework 'net5.0' is out of support and will not receive security updates in the future. Please refer to https://aka.ms/dotnet-core-support for more information about the support policy. [/app/Shadowsocks/Shadowsocks.csproj]
/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.Sdk.FrameworkReferenceResolution.targets(90,5): error NETSDK1100: To build a project targeting Windows on this operating system, set the EnableWindowsTargeting property to true. [/app/Shadowsocks.WPF/Shadowsocks.WPF.csproj]

Build FAILED.

/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.EolTargetFrameworks.targets(29,5): warning NETSDK1138: The target framework 'net5.0' is out of support and will not receive security updates in the future. Please refer to https://aka.ms/dotnet-core-support for more information about the support policy. [/app/Shadowsocks/Shadowsocks.csproj]
/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.Sdk.FrameworkReferenceResolution.targets(90,5): error NETSDK1100: To build a project targeting Windows on this operating system, set the EnableWindowsTargeting property to true. [/app/Shadowsocks.WPF/Shadowsocks.WPF.csproj]
    1 Warning(s)
    1 Error(s)

Time Elapsed 00:00:01.17
"""

    expected_version = "17.3.2+561848881"
    expected_errors = [
        NETSDKError(
            code='NETSDK1100',
            message='To build a project targeting Windows on this operating system, set the EnableWindowsTargeting property to true.',
            url='https://learn.microsoft.com/en-us/dotnet/core/tools/sdk-errors/netsdk1100',
            file_path='/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.Sdk.FrameworkReferenceResolution.targets',
            line_number=90,
            char_number=5,
            project_file='/app/Shadowsocks.WPF/Shadowsocks.WPF.csproj'
        )
    ]

    parser = BuildLog.parse(log_text)

    assert parser.version == expected_version, "Version mismatch"
    assert parser.errors == expected_errors, "Errors mismatch"

def test_netsdk_1045():
    """
    Although functionally not different from any other NETSDK error, we want to make sure we can parse NETSDK1045.
    This informative error tells us which version of .NET SDK we need to install.
    """
    log_text = """MSBuild version 17.3.2+561848881 for .NET
  Determining projects to restore...
/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.TargetFrameworkInference.targets(144,5): error NETSDK1045: The current .NET SDK does not support targeting .NET 7.0.  Either target .NET 6.0 or lower, or use a version of the .NET SDK that supports .NET 7.0. [/app/src/Web/Web.csproj]

Build FAILED.

/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.TargetFrameworkInference.targets(144,5): error NETSDK1045: The current .NET SDK does not support targeting .NET 7.0.  Either target .NET 6.0 or lower, or use a version of the .NET SDK that supports .NET 7.0. [/app/src/Web/Web.csproj]
    0 Warning(s)
    1 Error(s)

Time Elapsed 00:00:05.92
"""

    expected_version = "17.3.2+561848881"
    expected_errors = [
        NETSDKError(
            code='NETSDK1045',
            message='The current .NET SDK does not support targeting .NET 7.0.  Either target .NET 6.0 or lower, or use a version of the .NET SDK that supports .NET 7.0.',
            url='https://learn.microsoft.com/en-us/dotnet/core/tools/sdk-errors/netsdk1045',
            file_path='/usr/share/dotnet/sdk/6.0.417/Sdks/Microsoft.NET.Sdk/targets/Microsoft.NET.TargetFrameworkInference.targets',
            line_number=144,
            char_number=5,
            project_file='/app/src/Web/Web.csproj'
        )
    ]

    parser = BuildLog.parse(log_text)

    assert parser.version == expected_version, "Version mismatch"
    assert parser.errors == expected_errors, "Errors mismatch"

@pytest.mark.skip(reason="No current defined behavior for general errors.")
def test_no_error_code():
    """Undefined behavior for errors that do not arise from MSBuild."""
    log_text = """The command could not be loaded, possibly because:
  * You intended to execute a .NET application:
      The application 'build' does not exist.
  * You intended to execute a .NET SDK command:
      A compatible .NET SDK was not found.

Requested SDK version: 8.0.100
global.json file: /app/global.json

Installed SDKs:

Install the [8.0.100] .NET SDK or update [/app/global.json] to match an installed SDK.

Learn about SDK resolution:
https://aka.ms/dotnet/sdk-not-found
"""
    parser = BuildLog.parse(log_text)
    assert parser.errors == []