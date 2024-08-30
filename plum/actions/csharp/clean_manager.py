from pathlib import Path
from typing import Union
from plum.actions._docker_runner import DockerRunner

class CleanManager:
    """Handle C# artifacts cleaning via Docker to avoid ownership issues."""

    DEFAULT_CLEAN_COMMAND = "dotnet clean"

    def __init__(
            self,
            repo_full_path: Union[Path, str],
            docker_runner: DockerRunner,
        ) -> None:
        self.repo_path = Path(repo_full_path)
        """Full path to the repo to clean."""
        self.docker = docker_runner
        """Docker runner to use for the clean."""

    def remove_directory(self) -> tuple[int, str, str]:
        """Remove the entire directory."""
        # Due to Linux not allowing removal of the cwd,
        # we need to move up a directory before removing the entire directory.
        return_code, stdout, stderr = self.docker.run_multi_command(
            commands=[
                "cd ../",
                f"rm -rf {self.docker.mount_dir}/*", # Remove all non-hidden
                f"rm -rf {self.docker.mount_dir}/.*", # Remove all hidden
            ],
            repo_path=self.repo_path,
        )

        # Docker removed the directory contents, so we need to remove the local directory as well.
        self.repo_path.rmdir()

        return {
            "success": return_code == 0,
            "stdout": stdout,
            "stderr": stderr
        }

    def clean(self) -> tuple[int, str, str]:
        """Clean the C# artifacts."""
        return_code, stdout, stderr = self.docker.run_multi_command(
            commands=[
                "dotnet restore",
                CleanManager.DEFAULT_CLEAN_COMMAND
            ],
            repo_path=self.repo_path,
        )

        return {
            "success": return_code == 0,
            "stdout": stdout,
            "stderr": stderr
        }
