"""Tasks for discovering typescript functions"""
from plum.harnesslib.tasks.syntax import DiscoverFunctions
from plum.harnesslib.data_model import ClonedRepoInfo, Function
from plum.harnesslib.languages import Language
from plum.harnesslib.languages.javascript.syntax import JavascriptDiscoverFunctions


class TypescriptDiscoverFunctions(DiscoverFunctions):
    """Task for discovering the functions in a Typescript repo."""

    def __init__(self, repo_info: ClonedRepoInfo):
        """Create a new task for discovering functions in a Python repo.
        :param repo_info: The locally cloned repo to process.
        """
        super().__init__(repo_info)
        self._javascript_discover_funcs = JavascriptDiscoverFunctions(
            repo_info, language=Language.Typescript)

    def execute(self) -> list[Function]:
        """Discover typescript functions
        Returns:
            list[Function]: list of typescript functions
        """
        return self._javascript_discover_funcs.execute()

