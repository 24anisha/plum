"""Tasks are the composable building blocks of computation for an experiment."""

from plum.harnesslib.languages import Language
from plum.harnesslib.languages.javascript.syntax import JavascriptDiscoverFunctions
from plum.harnesslib.languages.python.env import CreatePythonEnvironment
from plum.harnesslib.languages.python.dependencies import PythonRepoDependencyInstaller
from plum.harnesslib.languages.javascript.dependencies import JavascriptRepoDependencyInstaller

from plum.harnesslib.languages.python.syntax import PythonDiscoverFunctions

from plum.harnesslib.languages.typescript.syntax import TypescriptDiscoverFunctions
from plum.harnesslib.tasks.dependencies import DependencyInstaller
from plum.harnesslib.tasks.syntax import DiscoverFunctions
from plum.harnesslib.tasks.task import SingleResultTask, MultiResultTask, TaskResult
from plum.harnesslib.util.task_factory import LanguageSpecificTaskFactory


discover_functions = LanguageSpecificTaskFactory[DiscoverFunctions]()
discover_functions.register(Language.Python, PythonDiscoverFunctions)
discover_functions.register(Language.Javascript, JavascriptDiscoverFunctions)
discover_functions.register(Language.Typescript, TypescriptDiscoverFunctions)

install_dependencies = LanguageSpecificTaskFactory[DependencyInstaller]()
install_dependencies.register(Language.Python, PythonRepoDependencyInstaller)
install_dependencies.register(Language.Javascript, JavascriptRepoDependencyInstaller)



# GetGenericBodies = LanguageSpecificTaskFactory[GetGenericBodies]()
# GetGenericBodies.register(Language.Python, PythonGetGenericBodies)
# GetGenericBodies.register(Language.Javascript, JavascriptGetGenericBodies)

__all__ = [
    "JavascriptDiscoverFunctions",
    # "JavascriptGetGenericBodies",
    # # "PythonGetGenericBodies",
    "CreatePythonEnvironment",
    "PythonRepoDependencyInstaller",
    "JavascriptRepoDependencyInstaller",
    "PythonDiscoverFunctions",
    "TypescriptDiscoverFunctions",
    "GetGenericBodies",
    "DependencyInstaller",
    "SingleResultTask",
    "MultiResultTask",
    "TaskResult",
    "discover_functions",
    "install_dependencies"
    # "trim_function_body",
]
