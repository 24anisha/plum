"""cleaning up the API and making it non specific to test generation (potentially to be renamed)"""
import logging
from plum.environments.cpp_repo import CppRepository
from plum.environments.csharp_repo import CsharpRepository
from plum.environments.java_repo import JavaRepository
from plum.environments.js_repo import JavascriptRepository
from plum.environments.py_repo import PythonRepository

# __name__ is name of module represented by this file (nothing above it)
# handler: sets rules for log formatting (location, when to log)
# NullHandler: clears logging handlers set by any dependent packages

# top level logger for whole project
# Every other logger will be a child of this logger
logging.basicConfig(level=logging.info)
logging.getLogger(__name__).addHandler(logging.NullHandler())

# conventional way to annotate logger
# FORMATTER = logging.formatter('%(asctime)s | %(levelname)s: %(message)s')

# general Repository factory function
def Repository(
        language: str,
        base,
        repo_path="",
        commit_sha="",
        focal_functions=[],
):
    """
    Takes input string language and returns the corresponding Repository object
    """
    language = language.lower()
    if language == "python":
        return PythonRepository(base, repo_path, commit_sha, focal_functions, language)
    elif language == "java":
        return JavaRepository(base, repo_path, commit_sha, focal_functions, language)
    elif language == "cpp":
        return CppRepository(base, repo_path, commit_sha, focal_functions, language)
    elif language == "csharp":
        return CsharpRepository(base, repo_path, commit_sha, focal_functions, language)
    elif language == "javascript" or language == "javascript":
        return JavascriptRepository(base, repo_path, commit_sha, focal_functions, language)
    else:
        raise ValueError(f"unsupported langauge: {language}")