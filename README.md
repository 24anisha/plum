# PLUM Pipeline

PLUM, or Programming Language Understanding Metrics, is a set of tools that enable users to interact with Large Language Models given the context of some environment (this could be a directory, a GitHub repo, etc). This package handles environments in Python, Javascript, Typescript and Java.

PLUM takes the environment input by the user and processes it to create a state object containing pertinent information such as the functions in the environment and the required dependencies. From there, it allows the user to take actions on this environment object and interface with a Large Language Model with the context of their environment.


## Table of Contents
------------------
* [PLUM Pipeline](#PLUM-Pipeline)
   * [Installation](#Installation)
   * [Example Usages](#Usages)
      * [Interacting with an Environment in PLUM](#interacting-with-env-in-plum)
      * [Method Generation](#method-creation)
   * [Cleanup](#cleanup)
   * [Notes](#Notes)
      * [Known Bugs](#known-bugs)

-------------------
## Installation
Create a virtual environment using `conda create --name plum-env python=3.10`.

`conda activate plum-env`

`pip install -e .`

Set the `OPENAI_API_KEY` environment variable to be your key to the Azure endpoint of the ChatGPT model

--------------------
## Example Usages

### Simple Example ###
This script in scripts/plum_example.py shows how to initialize a repository object and an instance of the actions class. In the example, we print the list of functions found in the repo, and print the test report yielded from running the test suite. A good example repo to try with is --repo_path johanrosenkilde/nasty_python.
```python
from plum.environments.py_repo import PythonRepository
from plum.actions.py_actions import PythonActions
import click

@click.command()
@click.option('--base', help='Base path at which to clone the git repo')
@click.option('--repo_path', help='"username/reponame"')
def run_one_repo(base, repo_path):

    repo = PythonRepository(base, repo_path)
    repo.setup(cleanup=True)
    functions = repo.get_functions()
    print(functions)
    actions = PythonActions(repo)

    control_test_report = actions.run_test_suite()
    print(control_test_report)

def main():
    run_one_repo()

if __name__ == "__main__":
    main()
```
### Interacting with an Environment in PLUM ###
Here is an example of how to interact with a GitHub repository environment with plum. This shows some, but not all the 
available functionality of plum.

```python
from plum.environments.py_repo import PythonRepository
from plum.actions.py_actions import PythonActions

def method_iteration(repo_name, base):
    """
    Example experimental pipeline for one git repo: run the tests in the repo & get a list of covered functions.
    Then, overwrite one of the functions from the repo with a "hello world" print statement, and see which tests fail.
    :param repo: 'owner/repo_name' of a git-cloneable repo
    :param base: path to the directory in which to clone the git repo
    """

    # Initialize PythonRepository environment object
    repo = PythonRepository(base, repo_name)
    repo.setup()
    functions = repo.get_functions()

    # initialize instance of PythonActions class, which has functionality for interacting with the environment object
    plum = PythonActions(repo)

    # get a JSON report of the result of running the test suite on the repo
    control_test_report = plum.run_test_suite()

    # get a list of functions in the repo that are covered by the repo's tests
    covered_functions = plum.get_covered_functions()

    # Iteratively move through the functions in the given repo
    for fnhash, function in functions.items():
        if fnhash in covered_functions:

            # Function objects represent each of the functions in the repo, and have attributes such as the function body
            new_function = function
            new_function.body = "   print('hello world')"

            # save original file contents before writing new function to file
            file_path = repo.base / repo.internal_repo_path / function.relative_path
            original_file_contents = open(file_path).read()

            # write the function's new body to the original file and re-run the test suite to see
            # which test cases fail
            plum.write_snippet_to_file(new_function, file_path, snippet_type='function')
            test_report = plum.run_test_suite()

            failed_tests = plum.utils.test_report_parsers.get_pytest_test_failures(control_test_report, test_report)
            print(failed_tests.keys())

            # rewrite the original file contents
            with open(file_path, "w") as f:
                f.write(original_file_contents)
```

### Method Generation ###
To see a full example interfacing with the OpenAI API to generate new method bodies based on method docstrings, see `scripts/method_generation_experiments.py`.

-----------------

## Test Evaluation
We generate tests in [Jest](https://jestjs.io) or [Mocha](https://mochajs.org) for JavaScript and TypesScript, and [PyTest](https://docs.pytest.org/en/7.2.x/) for Python. We use reporters from these testing libraries to determine whether tests pass or fail, and to determine coverage.

-----------------
## Cleanup
The code in this package generates many files and directories. To remove the generated files and reset your
directory to its state before running the package, call the cleanup function on your environment object.
-----------------
## Notes
- The cleanup function is not called by default in `setup()`, but it can be. Set the cleanup flag to True when calling `setup()` if you want to delete
to remove previously cloned or generated files for that repo.
### Known Bugs
- If you pass a relative path in as the base path to the environment object, the code will not work. Base should be an absolute path.

