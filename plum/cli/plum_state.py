import git
from json import loads
import os
from pathlib import Path
from typing import Optional, Union

from plum.configuration.config_loader import PlumConfigurationConcurrencyManager
from plum.configuration.configuration_model import SimplifiedRepository
from plum.configuration.detailed_configuration_model import DetailedRepository, KnownRepositoryDetails
from plum.constants import PLUM_FOLDER

def _ls_remote_head_hash(url: str) -> Optional[str]:
    """Get the HEAD hash of a remote repository.
    Will return None if the repository is private and the user does not have access."""
    # Save the OS environment variables
    # These are used to prevent git from asking for credentials
    old_git_terminal_prompt = os.environ.get('GIT_TERMINAL_PROMPT', None)
    old_git_askpass = os.environ.get('GIT_ASKPASS', None)
    os.environ['GIT_TERMINAL_PROMPT'] = '0'
    os.environ['GIT_ASKPASS'] = '0'

    # Fetch the commit hash using the Git binary
    g = git.Git()
    try:
        # Fetches all remotes hashes with the string HEAD in its tag
        # Could potentially pull multiple hashes:
        # ex)
        # 123abc    HEAD
        # 456def    refs/remotes/origin/HEAD
        # 890ghi    refs/remotes/pr1/HEAD
        all_lines = g.ls_remote(url, "HEAD")
        for lines in all_lines.split('\n'):
            commit_hash, _tag = lines.split('\t')
            if _tag == "HEAD":
                break
    except git.exc.GitCommandError as e:
        commit_hash = None
    finally:
        # Restore the OS environment variables
        if old_git_terminal_prompt is not None:
            os.environ['GIT_TERMINAL_PROMPT'] = old_git_terminal_prompt
        else:
            del os.environ['GIT_TERMINAL_PROMPT']
        if old_git_askpass is not None:
            os.environ['GIT_ASKPASS'] = old_git_askpass
        else:
            del os.environ['GIT_ASKPASS']
    return commit_hash

class PlumState:
    """Holds and controls the state of Plum"""
    def __init__(self, working_directory: Optional[Union[str, os.PathLike]] = None):
        self.cwd = Path(working_directory or os.getcwd())
        """Working directory of the configuration reader."""

        self.config_manager = PlumConfigurationConcurrencyManager.get_manager(self.cwd)
        """Concurrency manager for the configuration files."""

    def init(self):
        """Initialize a Plum project in the current working directory.

        Returns:
            bool: True if the project was initialized, False if it was already initialized
        """
        # Create the .plum directory if it doesn't exist
        Path(self.cwd / PLUM_FOLDER).mkdir(exist_ok=True)

        # Check if the config file exists, if not, write it
        self.config_manager.initialize()

        # Add the plum folder to the .gitignore file
        gitignore_file = self.cwd / ".gitignore"
        if gitignore_file.exists():
            # Check if the .plum folder is already in the .gitignore file
            with open(gitignore_file, 'r') as f:
                if PLUM_FOLDER not in f.read():
                    # Add the .plum folder to the .gitignore file
                    with open(gitignore_file, 'a') as f:
                        f.write("\n" + PLUM_FOLDER)

    def _unique_identifier(self, github_url: str, commit_hash: str) -> str:
        """Generate a unique identifier for a repository.

        Args:
            git_url (str): URL of the repository
            commit_hash (str): Commit hash of the repository

        Returns:
            str: Unique identifier for the repository
        """
        return github_url.split('/')[-2] + "--" + github_url.split('/')[-1] + "--" + commit_hash[:6]

    def _update_configs(
            self,
            config: dict,
            config_details: dict,
            group: str,
            git_url: str,
            commit_hash: Optional[str] = None,
            dir_name: str = None
        ):
        """Update the configuration files with the new repository."""
        # If the commit hash is not provided, get it from the remote repository
        if not commit_hash:
            commit_hash = _ls_remote_head_hash(git_url)
        if commit_hash == None:
            return False, f"Error: Failed to get the commit hash for {git_url}. Is the repository private or deleted?"

        # Generate a unique directory name from the Git URL and commit hash
        u_id = self._unique_identifier(git_url, commit_hash)
        dir_name = u_id if not dir_name else dir_name

        # Add the new entry under the specified group
        config.groups.setdefault(group, {})[u_id] = SimplifiedRepository(
            url=git_url,
            commit=commit_hash
        )
        detail = KnownRepositoryDetails(
            repo=DetailedRepository(
                url=git_url,
                commit=commit_hash,
                local_dir=dir_name
            ),
            env=None
        )
        config_details.groups.setdefault(group, {})[u_id] = detail

        return True, ""

    def read(self):
        """Read the Plum configuration files.

        Returns:
            Tuple[SimplifiedConfiguration, DetailedConfiguration]:
                The configuration and details, respectively. None if the file does not exist.
        """
        config, config_details = self.config_manager.read()
        return config, config_details

    def add(self, group: str, git_url: str, commit_hash: Optional[str] = None, dir_name:str = None):
        """Add a new entry to the Plum configuration."""
        # Load existing configuration
        config, config_details = self.config_manager.read()
        if not config:
            return False, "Error: Failed to read plum.config.json"
        if not config_details:
            return False, "Error: Failed to read plum.lock.json"

        success, message = self._update_configs(
            config=config,
            config_details=config_details,
            group=group,
            git_url=git_url,
            commit_hash=commit_hash,
            dir_name=dir_name
        )
        if not success:
            return False, message

        # Write the updated configuration back to the file
        self.config_manager.write(config, config_details)

        return True, f"Added {dir_name} under group '{group}'."

    def add_json_array(self, group, json_file):
        """Add entries from a JSON file to the Plum configuration.
        Expects the file to be a JSON array with nothing but Git URLs."""
        # Load existing configuration
        config, config_details = self.config_manager.read()
        if not config:
            return False, "Error: Failed to read plum.config.json"
        if not config_details:
            return False, "Error: Failed to read plum.lock.json"

        # Add the new entries
        with open(json_file, 'r') as f:
            entries = loads(f.read())
        for url in entries:
            success, message = self._update_configs(
                config=config,
                config_details=config_details,
                group=group,
                git_url=url
            )
            if not success:
                print(f"Skipping {url}:", message)

        # Write the updated configuration back to the file
        self.config_manager.write(config, config_details)

        return True, f"Added entries from {json_file} under group '{group}'."

    def add_jsonl(self, group, jsonl_file, url_key, commit_key):
        """Add entries from a JSONL file to the Plum configuration."""
        # Load existing configuration
        config, config_details = self.config_manager.read()
        if not config:
            return False, "Error: Failed to read plum.config.json"
        if not config_details:
            return False, "Error: Failed to read plum.lock.json"

        # Add the new entries
        with open(jsonl_file, 'r') as f:
            for line in f:
                entry: dict = loads(line)

                success, message = self._update_configs(
                    config=config,
                    config_details=config_details,
                    group=group,
                    git_url=entry[url_key],
                    commit_hash=entry.get(commit_key, None),
                    dir_name=None
                )
                if not success:
                    print(f"Skipping {entry[url_key]}:", message)

        # Write the updated configuration back to the file
        self.config_manager.write(config, config_details)

        return True, f"Added entries from {jsonl_file} under group '{group}'."