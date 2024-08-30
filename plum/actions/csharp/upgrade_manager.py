import logging
from pathlib import Path
from typing import Union

from plum.actions._docker_runner import DockerRunner


class UpgradeManager():
    def __init__(
        self,
        repo_full_path: Union[Path, str],
        docker_runner: DockerRunner,
        upgrade_to_version: str,
        timeout=60,
    ):
        ## Docker Configuration
        self.repo_path = repo_full_path
        self.docker = docker_runner

        ## Upgrade Parameters
        self.timeout = timeout
        """Timeout in seconds for the build command."""

        self.upgrade_to_version = f"net{upgrade_to_version}"

    def _setup_upgrade_tool_command(self) -> str:
        return 'dotnet tool install --global upgrade-assistant'

    def _create_upgrade_tool_command(self) -> list[str]:
        assert self.upgrade_to_version, "Upgrade to version can't be None"
        commands = []
        commands.append("export PATH=\"$PATH:/root/.dotnet/tools\"")
        commands.append(self._setup_upgrade_tool_command()) 
        commands.append("export DOTNET_UPGRADEASSISTANT_SKIP_FIRST_TIME_EXPERIENCE=\"true\"")

        # First add the git configuration command.
        commands.append(f"git config --global --add safe.directory {self.docker.mount_dir}")

        # Second find all the csproj files
        # then run upgrade tool command on each csproj file
        commands.append(f'find . -name "*.csproj" -type f -exec upgrade-assistant upgrade --non-interactive -o Inplace -f {self.upgrade_to_version} {{}} \;')

        return commands

    def upgrade(self):
        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "attempt_details": [],
        }

        commands = self._create_upgrade_tool_command()
        return_code, stdout, stderr = self.docker.run_multi_command(
            commands=commands,
            repo_path=self.repo_path,
            timeout=self.timeout
        )

        if return_code == 0:
            logging.info("Upgrade process completed successfully")
            result["success"] = True
        else:
            logging.error(
                f"Upgrade failed: {self.repo_path}. "
                f"({self.docker.image}:{self.docker.tag}) "
            )
        
        result["stdout"] = stdout
        result["stderr"] = stderr
        return result