import os, re
import subprocess
import shlex
import numpy as np
import json
import warnings
import autopep8
from plum.utils.logger import Logger

def fnhash(f):
    """
    Hash for the name of each parsed function.
    TODO change so not only .py is removed
    """
    path_hash = str(f.relative_path).replace("/", "--").replace(".py", "")
    return "--".join([f.name, str(f.start_line), path_hash])


def write_data_jsonl(datapoint, writepath):
    """
    Writes the data for each focal method from one repo 
    to a jsonl file This jsonl
    file contains the text of all the generated tests, as well
    as the evaluation of each test (NOTE: evaluation for python is currently not correct)
    :param datapoint: the data to write to the jsonl file. Either one dict representing one line
        of the jsonl file, or a list of dicts representing multiple lines of the jsonl file
    :param writepath: the path to the jsonl file to write to
    """
    if not isinstance(datapoint, list):
        datapoint = [datapoint]

    with open(writepath, 'a', encoding='utf-8') as f:
        for d in datapoint:
            json.dump(d, f, ensure_ascii=False)
            f.write('\n')


def quiet_call(cmd, **kwargs):
    """ execute cmd in a subprocess and hide stdout and stderr """
    return subprocess.call(
        shlex.split(cmd),
        **kwargs
    )  # call and suppress output
    # return subprocess.call(
    #     shlex.split(cmd),
    #     stdout=open(os.devnull, "w"),
    #     stderr=open(os.devnull, "w"),
    #     **kwargs,
    # )  # call and suppress output



def clone_repository(
    repo_url, directory, multi_options=None, env=None, commit=None, timeout=70
):
    """
    Clone a github repo URL into directory
    NOTE: for cloning Azure DevOps you may set the environment
    variable B64_PAT based on a personal access token, e.g.
        MY_PAT=yourPAT  # replace "yourPAT" with your actual PAT
        export B64_PAT=$(printf "%s"":$MY_PAT" | base64)

    Parameters
    ----------
    repo_url: str
        URL of git repository
    directory: str/Path
        string or Path of directory to place clone into
    multi_options: List[str] (optional)
        list of git clone command line options, defaults
        to ['--depth=1'] to grab first commit only
    env: Dict[str, str] (optional)
        environment variables in which to run git clone,
        defaults to {"GIT_TERMINAL_PROMPT": "0"} to turn off
        username and password prompts
    commit: str
        sha-1 commit hash to retrieve, slower as it requires retrieving
        the history of this commit
    commit: str
        sha-1 commit hash to checkout
    timeout: str
        number of second to allow clone to operate before quitting,
        a cheap heuristic to filter out data-heavy repositories.

    Returns
    -------
    msg: int
        error code, 0 means successful, 124 is a timeout, 128+ is
        some clone failure
    """
    cmdlist = [f"timeout {timeout} git"]
    if "B64_PAT" in os.environ:
        cmdlist.append(f'-c http.extraHeader="Authorization: Basic {os.environ["B64_PAT"]}"')
    cmdlist.append("clone")
    cmdlist.extend(
        multi_options or ["--depth=1",]
    )
    cmdlist.append(f"{repo_url} {directory}")
    msg = quiet_call(
        " ".join(cmdlist), env=env or dict(os.environ, GIT_TERMINAL_PROMPT="0"),
    )
    if msg:
        Logger().get_logger().error(f"{repo_url} returned error {msg}")
        return msg

    if commit:
        cmd = f"timeout {timeout} git fetch origin {commit}"
        msg = quiet_call(
            cmd, env=env or dict(os.environ, GIT_TERMINAL_PROMPT="0"), cwd=directory
        )
        if msg:
            return msg
        msg = quiet_call(f"git checkout {commit}", cwd=directory)

    return msg


def get_head_commit_hash(repo_directory):
    try:
        return (
            subprocess.check_output(
                shlex.split(f"git rev-parse HEAD"),
                cwd=repo_directory,
                stderr=open(os.devnull, "w"),
            )
            .decode("utf-8")
            .strip()
        )
    except subprocess.CalledProcessError:
        return ""


def pass_at_k(n, k, fn_results):
    """
    :param n: total number of samples
    :param c: number of correct samples
    :param k: k in pass@k
    """
    c = 0
    for gen_dict in fn_results:
        c += gen_dict["success"]

    if n - c < k: return 1.0
    return 1.0 - np.prod(1.0 - k /
            np.arange(n - c + 1, n + 1))


def get_test_package(package_json):
    """
    For use with JS and TS
    Returns the testing framework used in the repo natively
    params:
        package_json: path to package.json file
    returns:
        test_framework: name of test framework used 
        (currently supported options are mocha and jest)
    """
    with open(package_json, "r") as package:
        pkg_dict = json.load(package)

    if 'scripts' in pkg_dict and 'test' in pkg_dict['scripts']:
        test_command = pkg_dict['scripts']['test']
        if "mocha" in test_command:
            return "mocha"
        elif "jest" in test_command:
            return "jest"
        else:
            return None
    else:
        return None
    

def fix_indentation(source_string):
    """
    Fix indentation to be PEP8 compliant

    Parameters
    ----------
    source_string : str
        string of python source code
    timout: int (optional)
        second allowed for fix attempts

    Returns
    -------
    fixed_source_string : str
        fixed source string

    Raises
    ------
    TimeoutException
        if any of the attempted fixes time out
    """

    with warnings.catch_warnings(): # don't print SyntaxWarnings
        warnings.simplefilter('ignore')
        return autopep8.fix_code(source_string, options={"select": ("E101",)})



def postprocess(markdown):
    code_snippets = re.findall(r"```python(.*?)```", markdown, re.DOTALL)
    return code_snippets[0] if code_snippets else None


# TODO update this to work outside of athenacommon
# def build_library(language: LanguageId, force_build=False):
#     """
#     Look for the tree sitter parser shared objects in `LANGDIR`, which
#     should have a
#         '$HOME/.cache/source-parser/tree-sitter-<lang>.so'
#     for each grammar subdirectory in located in
#         `$ATHENACOMMON_DIR/assets/tree-sitter/tree-sitter-<lang>`
#     If `LANGDIR` does not exist, build it and save it in that location.

#     Parameters
#     ----------
#     language : LanguageId
#         Language ID for language
#     force_build : True/False
#         force the system to re-build even if the parsers exist
#     """
#     if not LANGDIR.parent.exists():
#         LANGDIR.mkdir(parents=True)
#         LOGGER.info(f"Created directory {LANGDIR} for parsers")

#     reponame = f"tree-sitter-{language.value}"

#     src_dir = (DATADIR / reponame / PARSER_RELATIVE_PATH[language]).parent.parent
#     langlib = LANGDIR / f"{reponame}.so"

#     if src_dir:
#         if not langlib.exists() or force_build:
#             Language.build_library(str(langlib), [src_dir])
#             LOGGER.info(f"Saved language shared object {langlib}")
#         else:
#             LOGGER.info(f"Found language shared object {langlib}")

#     else:
#         LOGGER.warning(
#             'Could not find "parser.c" within language ' f"parser in {langlib}"
#         )


# def get_language(language: Union[LanguageId, str], force_build=False) -> Language:
#     """
#     Get tree-sitter Language object for `language`

#     Parameters
#     ----------

#     language : Union[LanguageId, str]
#         unique language string or Language ID for language
#     force_build : True/False
#         force the system to re-build even if the parsers exist

#     Returns
#     -------
#     tree_sitter_language : tree_sitter.Language
#     """
#     if isinstance(language, str):
#         language = LanguageId(language)
#     build_library(language, force_build=force_build)

#     reponame = f"tree-sitter-{language.value}"
#     langlib = LANGDIR / f"{reponame}.so"
#     name = PARSER_SYMBOL_NAMES[language]
#     try:
#         return Language(str(langlib), "_".join(name.split("_")[2:]))
#     except ValueError as v_err:
#         LOGGER.warning(v_err)
#         cache_dir = Path(langlib).parent
#         LOGGER.warning(
#             f"Deleting cache {cache_dir} and re-trying to build and load tree-sitter Language"
#         )
#         rmtree(cache_dir)
#         build_library(language, force_build=True)
#         return Language(str(langlib), name)

#     raise RuntimeError(f"Could not find tree_sitter symbol in {langlib}")
