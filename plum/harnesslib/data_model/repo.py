"""Helper module for repo cloning and setup."""

from dataclasses import dataclass
from pathlib import Path

from plum.harnesslib.data_model.base import DataModel
from plum.harnesslib.languages import Language


@dataclass
class RepoInfo(DataModel):
    "Represents a repository"

    language: Language
    """
    The programming language considered for the repository.

    Multi-language repos are not supported at this time.
    """

    repo_name: str
    "The name of the repo"

    owner: str
    "The owner of the repo"

    @property
    def slug(self) -> str:
        "The slug of the repo, i.e. `owner/repo_name`"
        return self.owner + "/" + self.repo_name


@dataclass
class ClonedRepoInfo(RepoInfo):
    """
    Represents a repo that has been locally checked out, i.e. there is a Path to it.

    See also: :class:`harnesslib.tasks.CloneFromGitHub` returns a `ClonedRepoInfo`
    object.
    """

    folder_name: str
    "A file-name friendly version of the slug"

    clone_path: Path
    "The clone path of the repo"

    commit_sha: str
    "The Git commit SHA of the repo"


@dataclass
class Dependency(DataModel):
    """
    Represents a dependency of a repo.

    See also: :class:`harnesslib.tasks.DependencyInstaller` returns a list of installed
    `Dependency` objects.
    """

    package_name: str
    "The name of the package"

    version: str
    "The version of the package"

    language: Language
    "The programming language considered for the dependency"

    reason: str
    "The provenance of the dependency"
