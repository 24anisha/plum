from abc import ABC, abstractmethod
from typing import Union

from plum.harnesslib.data_model import ClonedRepoInfo, Dependency
from plum.harnesslib.tasks.task import MultiResultTask


class DependencyInstaller(MultiResultTask[Dependency], ABC):
    """
    Abstract base class for tasks that install dependencies of a target repo.
    """

    repo_info: ClonedRepoInfo
    "The cloned repo in which to install dependencies"

    def __init__(self, repo_info: ClonedRepoInfo, result_name: Union[str, None] = None):
        super().__init__(result_name=result_name)
        self.repo_info = repo_info

    @abstractmethod
    def execute(self) -> list[Dependency]:
        """
        Install the target repo's dependencies.
        """
