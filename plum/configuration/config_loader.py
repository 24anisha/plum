from json import load
import os
from pathlib import Path
from typing import Optional, Union
from filelock import FileLock


from plum.configuration.configuration_model import SimplifiedConfiguration
from plum.configuration.default_config import DEFAULT_CONFIG, DEFAULT_CONFIG_DETAILS
from plum.configuration.detailed_configuration_model import DetailedConfiguration
from plum.constants import CONFIG_FILE, CONFIG_DETAILS_FILE, CURRENTLY_ACTIVE_GROUPS, PLUM_FOLDER

open_configurations: dict[str, 'PlumConfigurationConcurrencyManager'] = {}
"""Dictionary of open configurations. Key is the working directory, value is the ConcurrencyManager."""

class PlumConfigurationConcurrencyManager():
    """Manages concurrency while reading and writing to the configuration files."""
    def __init__(self, working_directory: Optional[Union[str, os.PathLike]] = None):
        """Initialize the configuration reader."""

        self.cwd = Path(working_directory) or Path(os.getcwd())
        """Working directory of the configuration reader."""

        # Expected file paths for configuration files
        self.config_file_path = self.cwd / CONFIG_FILE
        """Path to the configuration file."""
        self.config_details_file_path = self.cwd / CONFIG_DETAILS_FILE
        """Path to the configuration details file."""
        self.active_groups_file_path = self.cwd / PLUM_FOLDER / CURRENTLY_ACTIVE_GROUPS
        """Path to the currently active groups file."""

        # File locks for ensuring concurrency
        self.config_lock = FileLock(
            self.cwd / PLUM_FOLDER / "plum.config.lock",
            timeout=0.1
        )
        """FileLock for the configuration file."""
        self.details_lock = FileLock(
            self.cwd / PLUM_FOLDER / "plum.lock.lock",
            timeout=0.1
        )
        """FileLock for the configuration lock file."""
        self.active_groups_lock = FileLock(
            self.cwd / PLUM_FOLDER / "currently_active_groups.lock",
            timeout=0.1
        )
        """FileLock for the currently active groups file."""

    @staticmethod
    def get_manager(working_directory: Optional[Union[str, os.PathLike]] = None):
        """Get the concurrency manager for the given working directory.

        Args:
            working_directory (Optional[str], optional): The working directory. Defaults to None.

        Returns:
            PlumConfigurationConcurrencyManager: The concurrency manager.
        """
        # Get absolute path
        working_directory = str(Path(
            working_directory if working_directory is not None else os.getcwd()
        ).resolve())

        if working_directory not in open_configurations:
            open_configurations[working_directory] = PlumConfigurationConcurrencyManager(working_directory)

        return open_configurations[working_directory]

    def initialize(self):
        """Initialize the configuration files if the files don't exist."""
        # Using filelock to ensure concurrency.
        with self.config_lock, self.details_lock:
            # If the default configuration files don't exist, create them.
            if not self.config_file_path.is_file():
                with self.config_file_path.open('w') as f:
                    f.write(DEFAULT_CONFIG.model_dump_json(indent=2))
            if not self.config_details_file_path.is_file():
                with self.config_details_file_path.open('w') as f:
                    f.write(DEFAULT_CONFIG_DETAILS.model_dump_json(indent=2))

    def read(self):
        """Read the configuration file.

        Returns:
            Tuple[SimplifiedConfiguration, DetailedConfiguration]:
                The configuration and details, respectively. None if the file does not exist.
        """
        config, details = None, None
        with self.config_lock, self.details_lock:
            if self.config_file_path.is_file():
                with self.config_file_path.open('r') as f:
                    config = load(f)
            if self.config_details_file_path.is_file():
                with self.config_details_file_path.open('r') as f:
                    details = load(f)

        config = SimplifiedConfiguration(**config) if config else None
        details = DetailedConfiguration(**details) if details else None

        return config, details

    def write(self, config: SimplifiedConfiguration, details: DetailedConfiguration):
        """Write the configuration file.

        Args:
            config (SimplifiedConfiguration): The configuration to write.
            details (DetailedConfiguration): The details to write.
        """
        with self.config_lock, self.details_lock:
            with self.config_file_path.open('w') as f:
                f.write(config.model_dump_json(indent=2))
            with self.config_details_file_path.open('w') as f:
                f.write(details.model_dump_json(indent=2))

    def read_active_groups(self):
        """Read the currently active groups.

        Returns:
            List[str]: The currently active groups.
        """
        with self.active_groups_lock:
            if self.active_groups_file_path.is_file():
                with self.active_groups_file_path.open('r') as f:
                    return f.read().splitlines()
            else:
                return []

    def write_active_groups(self, active_groups: list[str]):
        """Write the currently active groups.

        Args:
            active_groups (List[str]): The currently active groups.
        """
        with self.active_groups_lock:
            with self.active_groups_file_path.open('w') as f:
                f.write('\n'.join(active_groups))
