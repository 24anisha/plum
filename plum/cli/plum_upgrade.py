from json import dump
import os
from time import time
from typing import Optional, Type, Union
from pathlib import Path

from plum.actions._docker_runner import DockerRunner
from plum.actions.csharp.upgrade_manager import UpgradeManager as CSharpUpgrade
from plum.cli.plum_build import DEFAULT_BUILD_ENV
from plum.cli.plum_action import PlumAction
from plum.configuration.detailed_configuration_model import EnvironmentConfig, KnownRepositoryDetails
from plum.constants import PLUM_FOLDER

UPGRADE_CLASSES = {
    'cpp': None,
    'csharp': CSharpUpgrade,
    'java': None,
    'javascript': None,
    'python': None,
    'typescript': None,
}

def _get_upgrade_class(lang: str) -> Type:
    if lang in UPGRADE_CLASSES:
        return UPGRADE_CLASSES[lang]
    else:
        raise ValueError(f"Unsupported language: {lang}")

def _generate_config(id_config_tuple: tuple[str, str, Path, KnownRepositoryDetails]) -> tuple[str, KnownRepositoryDetails]:
    """Generate a KnownRepositoryDetails object."""
    config_id, lang, cwd, config = id_config_tuple

    res = _upgrade_single((lang, cwd, config))

    res["id"] = config_id
    return res

def _upgrade_single(path_config: tuple[str, Path, KnownRepositoryDetails]) -> dict:
    """Build a single repository."""
    lang, cwd, config = path_config

    upgrade_class = _get_upgrade_class(lang)

    full_path = cwd / config.repo.local_dir

    # Check if we know how to upgrade this repository
    if config.env is None:
        config.env = EnvironmentConfig(**DEFAULT_BUILD_ENV[lang])

    docker_runner = DockerRunner(
        image=config.env.image,
        tag=config.env.tag,
        mount_dir=config.env.work_dir
    )
    upgrade_manager = upgrade_class(
        repo_full_path=full_path,
        docker_runner=docker_runner,
        upgrade_to_version=config.env.tag,
        timeout=6000,
    )
    start = time()
    res = upgrade_manager.upgrade()
    duration = time() - start

    # Save successful build configurations
    res["env_config"] = upgrade_manager.docker.get_config()
    res["duration"] = duration

    return res

class PlumUpgrade(PlumAction):
    def __init__(
            self,
            lang: str,
            multiprocessing: bool,
            working_directory: Optional[Union[str, os.PathLike]] = None,
            specific_subdir: str = None,
        ):
        super().__init__(
            multiprocessing=multiprocessing,
            lang=lang,
            working_directory=working_directory
        )
        self.is_single_repo = specific_subdir is not None
        """Whether we are upgrading a single repository or all subdirectories in CWD."""
        self.specific_subdir = specific_subdir
        """Specific subdirectory to build."""

    def _retrieve_all_configurations(self) -> list[tuple[str, str, Path, KnownRepositoryDetails]]:
        """Retrieve all configurations from the configuration file."""
        active_groups = self.config_manager.read_active_groups()
        _, detailed_configs = self.config_manager.read()

        if len(active_groups) == 0:
            active_groups = ["default"]
        
        if detailed_configs is None:
            return []

        return [
            (
                config_id_key, 
                self.lang, 
                self.cwd,  
                KnownRepositoryDetails(
                    repo=config.repo,
                    env=EnvironmentConfig(
                        type=config.env.type if config.env else DEFAULT_BUILD_ENV[self.lang]['type'],
                        image=config.env.image if config.env else DEFAULT_BUILD_ENV[self.lang]['image'],
                        tag=str(float(config.env.tag) + 1) if config.env else DEFAULT_BUILD_ENV[self.lang]['tag'],
                        work_dir=config.env.work_dir if config.env else DEFAULT_BUILD_ENV[self.lang]['work_dir']
                    )
                )
            )
            for group in active_groups
            for config_id_key, config in detailed_configs.groups[group].items()
        ]

    def _update_configurations(self, results):
        """Update the configuration files."""
        active_groups = self.config_manager.read_active_groups()
        simple_configs, detailed_configs = self.config_manager.read()

        for successful_result in [r for r in results if r['success']]:
            for group in active_groups:
                if successful_result['id'] in detailed_configs.groups[group]: 
                    detailed_configs.groups[group][successful_result['id']].env = EnvironmentConfig(
                        **successful_result['env_config']
                    )
                    break

        self.config_manager.write(simple_configs, detailed_configs)

    def _save_results(self, results):
        """Save the results to respective temp files."""
        temp_dir = self.cwd / PLUM_FOLDER / "log" / "upgrade"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Wipe the directory
        for f in temp_dir.glob("*.json"):
            f.unlink()

        for result in results:
            with open(temp_dir / f"{result['id']}.json", 'w') as f:
                dump(result, f)

    def run(self, quiet: bool = False):
        if not self.is_single_repo:
            # Build for each project declared in the configuration file
            repo_configs = self._retrieve_all_configurations()
            if len(repo_configs) == 0 and not quiet:
                print("No configuration file found.")
                return

            results = self._run_all(_generate_config, repo_configs)

            self._update_configurations(results)
            self._summarize_results(results)
            self._save_results(results)

        else:
            raise NotImplementedError("Building a single repository is not yet supported.")