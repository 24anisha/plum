import os
from pathlib import Path
from time import time
from typing import Optional, Union

from plum.actions._docker_runner import DockerRunner
from plum.actions.csharp.clean_manager import CleanManager as CSharpClean
from plum.cli.plum_action import PlumAction
from plum.configuration.detailed_configuration_model import EnvironmentConfig, KnownRepositoryDetails

CLEAN_CLASSES = {
    'cpp': None,
    'csharp': CSharpClean,
    'java': None,
    'javascript': None,
    'python': None,
    'typescript': None,
}
DEFAULT_ENV = {
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

def _get_class(lang: str):
    return CLEAN_CLASSES.get(lang, None)

def _remove_single(id_config_tuple: tuple[str, str, Path, KnownRepositoryDetails]):
    """Remove a single repository."""
    config_id, lang, cwd, config = id_config_tuple

    clean_class = _get_class(lang)

    full_path = cwd / config.repo.local_dir

    # Check if we know how to clean this repository
    if clean_class is None:
        return {
            "success": False,
            "id": config_id,
            "stdout": "",
            "stderr": f"Unsupported language: {lang}",
        }
    if config.env is None:
        config.env = EnvironmentConfig(**DEFAULT_ENV[lang])

    # Check if the repository exists
    if not full_path.exists():
        return {
            "success": False,
            "id": config_id,
            "stdout": "",
            "stderr": f"Repository does not exist: {full_path}",
        }

    # Run the clean
    docker_runner = DockerRunner(
        image=config.env.image,
        tag=config.env.tag,
        mount_dir=config.env.work_dir,
    )
    start = time()
    res = clean_class(repo_full_path=full_path, docker_runner=docker_runner).remove_directory()
    duration = time() - start
    res["id"] = config_id
    res["duration"] = duration

    return res

def _clean_single(id_config_tuple: tuple[str, str, Path, KnownRepositoryDetails]):
    """Clean a single repository."""
    config_id, lang, cwd, config = id_config_tuple

    clean_class = _get_class(lang)

    full_path = cwd / config.repo.local_dir

    # Check if we know how to clean this repository
    if clean_class is None:
        return {
            "success": False,
            "id": config_id,
            "stdout": "",
            "stderr": f"Unsupported language: {lang}",
        }
    if config.env is None:
        return {
            "id": id,
            "success": False,
            "stdout": "",
            "stderr": f"No environment for {id}",
        }

    # Check if the repository exists
    if not full_path.exists():
        return {
            "success": False,
            "id": config_id,
            "stdout": "",
            "stderr": f"Repository does not exist: {full_path}",
        }

    # Run the clean
    docker_runner = DockerRunner(
        image=config.env.image,
        tag=config.env.tag,
        mount_dir=config.env.work_dir,
    )
    res = clean_class(repo_full_path=full_path, docker_runner=docker_runner).clean()
    res["id"] = config_id

    return res

class PlumClean(PlumAction):
    def __init__(
            self,
            lang: str,
            multiprocessing: bool,
            working_directory: Optional[Union[str, os.PathLike]] = None,
            full_clean: bool = False,
        ):
        super().__init__(
            multiprocessing=multiprocessing,
            lang=lang,
            working_directory=working_directory
        )

        self.full_clean = full_clean
        """Whether to perform a full removal of the directory and not just an artifacts clean up."""

    def run(self, quiet: bool = False):
        # Build for each project declared in the configuration file
        repo_configs = self._retrieve_all_configurations()
        if len(repo_configs) == 0 and not quiet:
            print("No configuration file found.")
            return

        fx_to_run = _remove_single if self.full_clean else _clean_single
        results = self._run_all(fx_to_run, repo_configs)

        if self.full_clean:
            # No groups should be active at this point. Erase the contents of the file.
            self.config_manager.write_active_groups([])

        self._summarize_results(results)
