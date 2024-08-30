from json import dump
import os
from pathlib import Path
from time import time
from typing import Optional, Type, Union


from plum.actions._docker_runner import DockerRunner
from plum.actions.csharp.build_manager import BuildManager as CSharpBuild
from plum.cli.plum_action import PlumAction
from plum.configuration.detailed_configuration_model import EnvironmentConfig, KnownRepositoryDetails
from plum.constants import PLUM_FOLDER

BUILD_CLASSES = {
    'cpp': None,
    'csharp': CSharpBuild,
    'java': None,
    'javascript': None,
    'python': None,
    'typescript': None,
}
"""Dictionary of supported languages and their corresponding build classes."""
DEFAULT_BUILD_ENV = {
    'cpp': None,
    'csharp': {
        'type': 'docker',
        'image': 'mcr.microsoft.com/dotnet/sdk',
        'tag': '6.0',
        'work_dir': '/app',
    },
    'java': None,
    'javascript': None,
    'python': None,
    'typescript': None,
}

def _get_build_class(lang: str) -> Type:
    if lang in BUILD_CLASSES:
        return BUILD_CLASSES[lang]
    else:
        raise ValueError(f"Unsupported language: {lang}")

def _generate_config(id_config_tuple: tuple[str, str, Path, KnownRepositoryDetails]) -> tuple[str, KnownRepositoryDetails]:
    """Generate a KnownRepositoryDetails object."""
    config_id, lang, cwd, config = id_config_tuple

    res = _build_single((lang, cwd, config))

    res["id"] = config_id
    return res

def _build_single(path_config: tuple[str, Path, KnownRepositoryDetails]) -> dict:
    """Build a single repository."""
    lang, cwd, config = path_config

    build_class = _get_build_class(lang)

    full_path = cwd / config.repo.local_dir

    # Check if we know how to build this repository
    if config.env is None:
        config.env = EnvironmentConfig(**DEFAULT_BUILD_ENV[lang])

    docker_runner = DockerRunner(
        image=config.env.image,
        tag=config.env.tag,
        mount_dir=config.env.work_dir,
    )
    build_manager = build_class(
        repo_full_path=full_path,
        docker_runner=docker_runner,
        timeout=600,
    )
    start = time()
    res = build_manager.build()
    duration = time() - start

    # Save successful build configurations
    res["env_config"] = build_manager.docker.get_config()
    res["duration"] = duration

    return res

class PlumBuild(PlumAction):
    def __init__(
            self,
            lang: str,
            multiprocessing: bool,
            working_directory: Optional[Union[str, os.PathLike]] = None,
            specific_subdir: str = None,
        ):
        """Initialize the Plum build manager.

        Args:
            lang (str): Language to build
            multiprocessing (bool): Whether to use multiprocessing
            working_directory (Optional[Union[str, os.PathLike]], optional): Plum project root. Defaults to the current working directory.
            specific_subdir (str, optional): Specific subdirectory to build. Defaults to None.
        """
        super().__init__(
            multiprocessing=multiprocessing,
            lang=lang,
            working_directory=working_directory
        )
        self.is_single_repo = specific_subdir is not None
        """Whether we are building a single repository or all subdirectories in CWD."""
        self.specific_subdir = specific_subdir
        """Specific subdirectory to build."""

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
        temp_dir = self.cwd / PLUM_FOLDER / "log" / "build"
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