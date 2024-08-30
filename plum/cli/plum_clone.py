from typing import Optional, Tuple, Union
import git
import os
from pathlib import Path

from tqdm import tqdm

from plum.cli._utils import multiprocess
from plum.configuration.config_loader import PlumConfigurationConcurrencyManager
from plum.configuration.detailed_configuration_model import KnownRepositoryDetails
from plum.constants import PLUM_FOLDER

def _clone_repo(id_config_tuple: tuple[str, Path, KnownRepositoryDetails]):
    """Clone a single repository."""
    _config_id, cwd, config = id_config_tuple

    repo_info = config.repo
    local_dir = cwd / config.repo.local_dir

    try:
        repo_url = repo_info.url
        commit_hash = repo_info.commit

        # Shallow clone
        git.Repo.clone_from(
            url=repo_url,
            to_path=local_dir,
            depth=1
        )

        # Checkout the correct commit
        # Fetch the specific commit if not in the shallow clone
        submodule_repo = git.Repo(local_dir)
        try:
            submodule_repo.git.checkout(commit_hash)
        except git.exc.GitCommandError:
            # Fetch more history and try again
            submodule_repo.git.fetch('origin', commit_hash)
            submodule_repo.git.checkout(commit_hash)
        return local_dir, None
    except Exception as e:
        return local_dir, f"Error: {e}"

class PlumClone:
    """Clones specified group or groups from the Plum configuration file."""
    def __init__(
            self,
            working_directory: Optional[Union[str, os.PathLike]] = None,
            groups=["default"],
            use_multiprocessing=True,
            limit=None,
        ):
        self.cwd = Path(working_directory or os.getcwd())
        """Plum project working directory."""

        self.groups = groups if groups else ["default"]
        self.use_multiprocessing = use_multiprocessing
        self.limit = limit

        self.config_manager = PlumConfigurationConcurrencyManager.get_manager(self.cwd)
        """Concurrency manager for the configuration files."""

    ## TODO: This is a necessary step, but we're going to just skip it for now.
    def _cross_validate_and_update_repos_to_clone(self):
        """Cross validate the configuration file and the configuration details file.
        If there are any missing details in the configuration details file, update them.

        Returns:
            list: List of repositories to clone
        """
        config, config_details = self.config_manager.read()

        # Check that the configuration file and the configuration details file are in sync
        # If they are not, update the configuration details file
        repos_to_clone = []

        for group in self.groups:
            for repo_id, repo_info in config.groups[group].items():
                # Using the repo_id, check the lock file for the details.
                # If the lock file doesn't have details, this is a good chance to update them.

                # Check that the repo_id exists in the lock file
                if repo_id not in config_details.groups[group]:
                    # Add the repo_id to the lock file
                    config_details.groups[group][repo_id] = {}

                # Check for a 'repo' key in the lock file
                if 'repo' not in config_details.groups[group][repo_id]:
                    config_details.groups[group][repo_id].repo = {
                        "url": repo_info.url,
                        "commit": repo_info.commit,
                        "local_dir": repo_id
                    }

                repos_to_clone.append(config_details.groups[group][repo_id].repo)

        return repos_to_clone

    def _retrieve_all_configurations(self):
        """Retrieve all configurations from the configuration file."""
        _, detailed_configs = self.config_manager.read()

        if detailed_configs is None:
            return []

        return [
            (config_id_key, self.cwd, config)
            for group in self.groups
            for config_id_key, config in detailed_configs.groups[group].items()
        ]

    def _clone_repos(self):
        """Clones the repositories specified in the configuration file."""
        ## TODO: This is a necessary step, but we're going to just skip it for now.
        # repos_to_clone = self._cross_validate_and_update_repos_to_clone()

        # Identify repos to clone
        repo_configs = self._retrieve_all_configurations()

        if self.limit:
            # Limit the number of repos to clone
            repo_configs = repo_configs[:self.limit]

        if self.use_multiprocessing:
            clone_results = multiprocess(_clone_repo, repo_configs)
        else:
            clone_results = [
                _clone_repo(repo_info) for repo_info in tqdm(repo_configs, total=len(repo_configs))
            ]

        # Return results for logging or further processing
        return clone_results

    def run(self, quiet=True):
        clone_results = self._clone_repos()

        # Create PLUM_FOLDER if it doesn't exist
        plum_path = self.cwd / PLUM_FOLDER
        if not plum_path.exists():
            plum_path.mkdir()

        # Save the active groups to the .plum directory
        # TODO: No check exists on whether all members of self.groups are valid groups nor if they successfully cloned.
        self.config_manager.write_active_groups(self.groups)

        total_count = len(clone_results)
        clone_error_count = len([result for _, result in clone_results if result is not None])

        if not quiet:
            if clone_error_count == 0:
                print(f"All {total_count} repositories cloned successfully.")
                return

            if clone_error_count > 0:
                print(f"{total_count - clone_error_count} repositories cloned out of {total_count} repos.")
            else:
                print(f"All {total_count} repositories cloned successfully.")

        return total_count, clone_error_count
