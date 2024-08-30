import pytest
from plum.environments.csharp_repo import CsharpRepository
from plum.actions.csharp_dotnet_actions import CsharpDotnetActions

# Constants for the test
DOCKER_IMAGE = "mcr.microsoft.com/dotnet/sdk"
DOCKER_TAG = "6.0"
REPO_FOLDER = "" # TODO: Update when we have set of test repos added as submodules.

@pytest.mark.skip("Set of test repos required as submodules.")
def test_csharp_build():
    """
    WIP entry point for .NET Actions.
    """
    # Setup the repository
    repo = CsharpRepository(REPO_FOLDER, "", language="csharp")
    plum = CsharpDotnetActions(repo, DOCKER_IMAGE, DOCKER_TAG)
    repo.setup(cleanup=True)

    # Execute the build process
    res = plum.build()

    # Assert that the build was successful
    assert res["status_result"] == "SUCCESS", "BUILD ERROR"
