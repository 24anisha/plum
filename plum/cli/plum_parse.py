from json import dump
from multiprocessing import Pool, cpu_count
import os
from pathlib import Path
from time import time
from tqdm import tqdm
from plum.actions.csharp.repository_parser import CSharpRepositoryParser
from plum.configuration.config_loader import PlumConfigurationConcurrencyManager
from plum.configuration.detailed_configuration_model import KnownRepositoryDetails
from plum.constants import PLUM_FOLDER

def _write_parse_results(id_config_tuple: tuple[str, Path, KnownRepositoryDetails]):
    """Find the target framework for a project."""
    config_id, cwd, config = id_config_tuple

    full_path = cwd / config.repo.local_dir

    write_path = cwd / PLUM_FOLDER / 'parse' / f"{config_id}.repo.json"
    write_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing to {write_path}...")

    repo_parser = CSharpRepositoryParser(full_path)
    try:
        repo_parser.parse()
        repo_dict = repo_parser.to_dict()

        with open(write_path, 'w') as f:
            dump(repo_dict, f, indent=2)

        return True
    except Exception as e:
        return False

class PlumParse:
    def __init__(self, multiprocessing: bool, working_directory: str):
        self.multiprocessing = multiprocessing

        self.cwd = Path(working_directory or os.getcwd())
        """Plum project working directory."""
        self.config_manager = PlumConfigurationConcurrencyManager(working_directory)
        """Concurrency manager for the configuration files."""

    def _retrieve_all_configurations(self):
        """Retrieve all configurations from the configuration file.
        TODO: Currently we hardcode the group to be 'default'.
        Fixing this requires API change + Plum change to reflect what's currently active.
        """
        _, detailed_configs = self.config_manager.read()

        if detailed_configs is None:
            return []

        return [
            (config_id_key, self.cwd, config)
            for config_id_key, config in detailed_configs.groups['default'].items()
        ]

    def _parse_all(
        self,
        repo_configs: list[tuple[str, Path, KnownRepositoryDetails]]
    ):
        """Parse all repositories."""
        if self.multiprocessing:
            num_processes = min(cpu_count() - 1, len(repo_configs), 60)

            with Pool(processes=num_processes) as pool:
                results = list(
                    tqdm(
                        pool.imap_unordered(_write_parse_results, repo_configs),
                        total=len(repo_configs)
                    )
                )
        else:
            results = [_write_parse_results(config) for config in repo_configs]

        return results

    def run(self, quiet: bool = False):
        """Parse all repositories."""
        repo_configs = self._retrieve_all_configurations()
        if len(repo_configs) == 0 and not quiet:
            print("No configuration file found.")
            return

        results = self._parse_all(repo_configs)

        return results