from pathlib import Path
import pytest


from plum.actions._docker_runner import DockerRunner

IMAGE = "fake_image"
TAG = "fake.tag"
MOUNT_DIR = "/app"


@pytest.mark.parametrize(
    argnames="input_path, expected",
    argvalues=[
        ("C:\\Users\\Test\\Repo", "C:/Users/Test/Repo"),
        (Path("C:\\Users\\Test\\Repo"), "C:/Users/Test/Repo"),
        ("/home/user/repo", "/home/user/repo"),
        ("C:/Users\\Test\\Repo\\subdir", "C:/Users/Test/Repo/subdir"),
        ("C:\\Users\\Test/Repo/subdir", "C:/Users/Test/Repo/subdir"),
    ],
    ids=[
        "Windows Path (String)",
        "Windows Path (Pathlib)",
        "Unix Path",
        "Mixed Path",
        "Mixed Path 2",
    ]
)
def test_repo_full_path_sterilization(input_path, expected):
    """Minor detail that needs to work correctly to support Windows execution."""
    sterilized_repo_path = DockerRunner.sterilize_path(input_path)

    assert sterilized_repo_path == expected, "Windows path not properly sterilized."

def test_partial_path_sterilization():
    """Path sterilization should also work for relative paths."""
    input_path = "Users\\Test\\Repo"
    expected = "Users/Test/Repo"
    sterilized_repo_path = DockerRunner.sterilize_path(input_path)

    assert sterilized_repo_path == expected, "Windows path not properly sterilized."

@pytest.mark.parametrize(
    argnames="repo_path, relative_work_dir, expected_command",
    argvalues=[
        ("C:/Users/Test/Repo", None, "docker run --rm -v C:/Users/Test/Repo:/app -w /app fake_image:fake.tag"),
        ("/home/user/repo", "src/fake_dir", "docker run --rm -v /home/user/repo:/app -w /app/src/fake_dir fake_image:fake.tag"),
        ("C:/Users/Test/Repo/subdir", "src", "docker run --rm -v C:/Users/Test/Repo/subdir:/app -w /app/src fake_image:fake.tag"),
    ]
)
def test_get_docker_command(repo_path, relative_work_dir, expected_command):
    """Test that _get_docker_command() generates the correct Docker command."""
    runner = DockerRunner(IMAGE, TAG, MOUNT_DIR)
    actual_command = runner._get_docker_command(repo_path, relative_work_dir)
    assert actual_command == expected_command, f"Expected {expected_command}, but got {actual_command}"

@pytest.mark.parametrize(
    argnames="repo_path, relative_work_dir, expected_command",
    argvalues=[
        ("C:\\Users\\Test\\Repo", "src","docker run --rm -v C:/Users/Test/Repo:/app -w /app/src fake_image:fake.tag"),
        (Path("C:\\Users\\Test\\Repo"), "src/a","docker run --rm -v C:/Users/Test/Repo:/app -w /app/src/a fake_image:fake.tag"),
        ("C:/Users\\Test\\Repo\\subdir", "src\\fake_dir","docker run --rm -v C:/Users/Test/Repo/subdir:/app -w /app/src/fake_dir fake_image:fake.tag"),
    ]
)
def test_docker_command_sterilization(repo_path, relative_work_dir, expected_command):
    """Test that the Docker command is correctly sterilized for various input paths."""
    runner = DockerRunner(IMAGE, TAG, MOUNT_DIR)
    actual_command = runner._get_docker_command(repo_path, relative_work_dir)
    assert actual_command == expected_command, f"Expected {expected_command}, but got {actual_command}"
