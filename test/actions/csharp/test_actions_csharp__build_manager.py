from pathlib import Path
import pytest


from plum.actions.csharp.build_manager import BuildManager


@pytest.mark.skip("Set of test repos required as submodules.")
def test_csharp_build():
    """
    WIP entry point for .NET Actions.
    """
    DOCKER_IMAGE = "mcr.microsoft.com/dotnet/sdk"
    DOCKER_TAG = "6.0"
    REPO_FOLDER = "" # TODO: Update when we have set of test repos added as submodules.

    # Setup the repository
    build_manager = BuildManager(
        repo_full_path=REPO_FOLDER,
        docker_work_dir="/app",
        docker_image=DOCKER_IMAGE,
        docker_tag=DOCKER_TAG,
        timeout=60,
        retry_limit=3,
    )

    # Execute the build process
    res = build_manager.build()

    # Assert that the build was successful
    assert res.success, "BUILD ERROR"
