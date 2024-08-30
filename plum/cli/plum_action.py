# plum/cli/plum_action.py
import os
from pathlib import Path
from typing import Callable, Optional, TypeVar, Union

from tqdm import tqdm

from plum.cli._utils import multiprocess
from plum.configuration.config_loader import PlumConfigurationConcurrencyManager
from plum.configuration.detailed_configuration_model import KnownRepositoryDetails

T = TypeVar('T')
"""Generic type used for PlumAction._run_all()"""

class PlumAction:
    def __init__(
        self,
        multiprocessing: bool,
        lang: Optional[str] = None,
        working_directory: Optional[Union[str, os.PathLike]] = None,
    ):
        self.lang = lang.lower()
        self.multiprocessing = multiprocessing
        self.cwd = Path(working_directory or os.getcwd())
        """Plum project working directory."""

        self.config_manager = PlumConfigurationConcurrencyManager.get_manager(self.cwd)
        """Concurrency manager for the configuration files."""

    def _find_configuration(self, subdir: str):
        """Find a single configuration for a specific subdirectory."""
        subdir = subdir.strip('/') # Need to trim all slashes from the subdir

        active_groups = self.config_manager.read_active_groups()
        _, detailed_configs = self.config_manager.read()

        if detailed_configs is None:
            return None, None

        for group in active_groups:
            for config_id_key, config in detailed_configs.groups[group].items():
                if config.repo.local_dir == subdir:
                    return config_id_key, config

        return None, None

    def _retrieve_all_configurations(self) -> list[tuple[str, str, Path, KnownRepositoryDetails]]:
        """Retrieve all configurations from the configuration file."""
        active_groups = self.config_manager.read_active_groups()
        _, detailed_configs = self.config_manager.read()

        if detailed_configs is None:
            return []

        return [
            (config_id_key, self.lang, self.cwd, config)
            for group in active_groups
            for config_id_key, config in detailed_configs.groups[group].items()
        ]

    def _summarize_results(self, results):
        """Summarize the results."""
        total_repos = len(results)
        successful_repos = sum(1 for result in results if result['success'])
        timedout_repos = sum(1 for result in results if result['stderr'] == "Timeout")
        success_rate = successful_repos / total_repos if total_repos > 0 else 0

        # Only count the durations if they exist
        durations = [result['duration'] for result in results if 'duration' in result]
        average_duration = sum(durations) / len(durations) if len(durations) > 0 else 0

        print("Summary Report:")
        print(f"Total Repositories Processed: {total_repos}")
        print(f"Successful: {successful_repos}")
        print(f"Timedout: {timedout_repos}")
        print(f"Success Rate: {success_rate:.2f}")
        print(f"Average Duration: {average_duration:.2f} seconds")

    def _run_all(self, fx_to_run: Callable[[T], dict], all_configs: list[T]):
        """Run a function for all configurations.

        Args:
            fx_to_run: The function to run.
            all_configs: The configurations to run the function on.
        """
        if self.multiprocessing:
            results = multiprocess(fx_to_run, all_configs)
        else:
            results = [fx_to_run(d) for d in tqdm(all_configs)]

        return results

    def run(self, quiet: bool = False):
        raise NotImplementedError("This method should be implemented by subclasses.")
