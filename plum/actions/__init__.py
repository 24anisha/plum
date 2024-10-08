"""cleaning up the API and making it non specific to test generation (potentially to be renamed)"""
import logging
from plum.actions.cpp_actions import CppActions
from plum.actions.csharp_dotnet_actions import CsharpDotnetActions
from plum.actions.java_mvn_actions import JavaMavenActions
from plum.actions.js_actions import JavascriptActions
from plum.actions.py_actions import PythonActions

# __name__ is name of module represented by this file (nothing above it)
# handler: sets rules for log formatting (location, when to log)
# NullHandler: clears logging handlers set by any dependent packages

# top level logger for whole project
# Every other logger will be a child of this logger
logging.basicConfig(level=logging.WARNING)
logging.getLogger(__name__).addHandler(logging.NullHandler())

# conventional way to annotate logger
# FORMATTER = logging.formatter('%(asctime)s | %(levelname)s: %(message)s')

# general Actions factory function
def Actions(
    
    language: str,
    environment,
    docker_image = None,
    docker_tag = None,
    docker_work_dir="/data",
    repo_name="",
    local_repository="",
):
    """
    Takes input string language and returns the corresponding Actions object
    """

    language = language.lower()
    if language == "cpp":
        return CppActions(environment, docker_image, docker_tag, docker_work_dir, repo_name, local_repository)
    elif language == "csharp":
        return CsharpDotnetActions(environment, docker_image, docker_tag, docker_work_dir, repo_name, local_repository)
    elif language == "java":
        return JavaMavenActions(environment, docker_image, docker_tag, docker_work_dir, repo_name, local_repository)
    elif language == "javascript" or language == "typescript":
        return JavascriptActions(environment)
    elif language == "python":
        return PythonActions(environment)
    else:
        raise ValueError(f"unsupported language: {language}")
