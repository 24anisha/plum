from json import dump
import os
from pathlib import Path
from time import time
from typing import Optional, Type, Union

from plum.actions._docker_runner import DockerRunner
from plum.actions.csharp.coverage_manager import CoverageManager as CSharpCoverage
from plum.cli.plum_action import PlumAction
from plum.configuration.config_loader import PlumConfigurationConcurrencyManager
from plum.configuration.detailed_configuration_model import KnownRepositoryDetails
from plum.constants import PLUM_FOLDER

COVERAGE_CLASSES = {
    'cpp': None,
    'csharp': CSharpCoverage,
    'java': None,
    'javascript': None,
    'python': None,
    'typescript': None,
}
"""Dictionary of supported languages and their corresponding build classes."""

def _get_class(lang: str) -> Type:
    return COVERAGE_CLASSES.get(lang, None)

def _coverage_single_repo(path_config: tuple[str, str, Path, KnownRepositoryDetails]):
    """Run coverage on a single repository."""
    id, lang, cwd, config = path_config

    coverage_class = _get_class(lang)
    if coverage_class is None:
        return {
            "id": id,
            "success": False,
            "stdout": "",
            "stderr": f"Unsupported language: {lang}",
        }

    # Check if we know how to build this repository
    if config.env is None:
        return {
            "id": id,
            "success": False,
            "stdout": "",
            "stderr": f"No environment for {id}",
        }

    docker_runner = DockerRunner(
        image=config.env.image,
        tag=config.env.tag,
        mount_dir=config.env.work_dir,
    )
    load_res = coverage_class.load(
        repo_full_path=cwd / config.repo.local_dir,
        docker_runner=docker_runner,
        timeout=420,
    )

    if not load_res["success"]:
        load_res['id'] = id
        return load_res

    coverage_manager = load_res["manager"]
    start = time()
    res = coverage_manager.run_coverage()
    duration = time() - start

    res["duration"] = duration
    res['id'] = id
    return res

class PlumCoverage(PlumAction):
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
        self.lang = lang.lower()
        self.multiprocessing = multiprocessing

        self.cwd = Path(working_directory or os.getcwd())
        """Plum project working directory."""

        self.is_single_repo = specific_subdir is not None
        """Whether we are targeting a single repository or all subdirectories in CWD."""
        self.specific_subdir = specific_subdir
        """Specific subdirectory to target."""

        self.config_manager = PlumConfigurationConcurrencyManager.get_manager(self.cwd)
        """Concurrency manager for the configuration files."""

    def _save_results(self, results):
        """Save the results of the build."""
        temp_dir = self.cwd / PLUM_FOLDER / "coverage"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Wipe the directory
        for file in temp_dir.iterdir():
            file.unlink()

        for result in results:
            with open(temp_dir / f"{result['id']}.txt", "w") as f:
                dump(result, f, indent=2)

    def run(self, quiet: bool = False):
        """Run the coverage manager."""
        if not self.is_single_repo:
            repo_configs = self._retrieve_all_configurations()
            if len(repo_configs) == 0 and not quiet:
                print("No configuration file found.")
                return

            results = self._run_all(_coverage_single_repo, repo_configs)
            self._summarize_results(results)
            self._save_results(results)

        else:
            id, config = self._find_configuration(self.specific_subdir)
            if config is None:
                if not quiet:
                    print(f"No configuration found for {self.specific_subdir}")
                return

            results = [_coverage_single_repo((id, self.lang, self.cwd, config))]
            self._summarize_results(results)
            self._save_results(results)
