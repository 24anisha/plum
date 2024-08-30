from typing import Union
from plum.harnesslib.data_model import ClonedRepoInfo, Function
from plum.harnesslib.tasks.task import MultiResultTask


class DiscoverFunctions(MultiResultTask[Function]):
    """
    Task for discovering the functions in a Python repo.
    """

    def __init__(self, repo_info: ClonedRepoInfo, result_name: Union[str, None] = None):
        super().__init__(result_name=result_name)
        self.repo_info = repo_info
