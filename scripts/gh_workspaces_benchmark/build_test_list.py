import os
from json import dump
from typing import Type
from tqdm import tqdm
import click

from plum.actions.actions import Actions
from plum.actions.js_actions import JavascriptActions
from plum.actions.py_actions import PythonActions
from plum.environments.js_repo import JavascriptRepository
from plum.environments.py_repo import PythonRepository
from plum.environments.repository import Repository
from scripts.gh_workspaces_benchmark._work_paths import (
    get_default_lang_list_path,
    get_default_repo_directory
)


@click.command()
@click.option('--base_path', default=get_default_repo_directory(), help='Base path for the directories.')
@click.option('--repo_file', default=get_default_lang_list_path(), help='Path to the file listing repositories with their languages.')
@click.option('--result_json', default="plum_benchmark.json", help='File to write results to.')
def main(base_path, repo_file, result_json):
    """Run through the specified folder and try to use PLUM on every repository listed."""
    with open(repo_file, "r") as file:
        txt_lines = [line.strip().replace('/', '--') for line in file if line.strip()]

    def find_directory(expected_start):
        """ Search for a directory that starts with the given expected_start string. """
        try:
            for item in os.listdir(base_path):
                if item.startswith(expected_start):
                    return item
            return None
        except FileNotFoundError:
            print(f"Base path not found: {base_path}")
        except Exception as e:
            print(f"An error occurred while listing directories in {base_path}: {e}")

    def write_to_file(data, filename=result_json):
        """Writes the provided data to the specified file."""
        with open(filename, "w") as f:
            dump(data, f, indent=2)

    # Detailed output initialization
    full_output = {
        "repo_init": {"success": [], "failure": []},
        "test": {"success": [], "failure": []},
        "coverage": {"success": [], "failure": []}
    }

    # Iterate through all folders which are not hidden
    for txt_line in tqdm(txt_lines):
        print(txt_line)
        directory, language = txt_line.split(",")
        matched_dir = find_directory(directory)

        if not matched_dir:
            print(f"Directory starting with {directory} not found.")
            continue

        full_path = os.path.join(base_path, matched_dir)

        if not os.path.isdir(full_path):
            print(f"{full_path} is not a directory.")
            continue

        print(f"Running PLUM on {full_path}: {language}")

        if language == "python":
            repo = PythonRepository(base=full_path)
            actions_class = PythonActions
        elif language == "javascript":
            repo = JavascriptRepository(base=full_path)
            actions_class = JavascriptActions
        elif language == "typescript":
            repo = JavascriptRepository(
                base=full_path,
                language="typescript"
            )
            actions_class = JavascriptActions
        else:
            print(f"Unsupported language: {language} for {full_path}")
            continue

        run_plum_actions(repo, actions_class, full_output)

        # Write current results to file after processing each repository
        write_to_file(full_output)

    summarize_results(full_output)

def run_plum_actions(repo: Repository, actions_class: Type[Actions], full_output: dict):
    """Runs initialization, tests, and coverage on the given repository using specified actions."""
    path_str = str(repo.base)
    try:
        repo.setup(
            cleanup=False,
            install_reqs=True
        )
        full_output['repo_init']['success'].append(path_str)
    except Exception as e:
        full_output['repo_init']['failure'].append(path_str)
        return

    plum = actions_class(repo)
    try:
        if plum.run_test_suite():
            full_output['test']['success'].append(path_str)
        else:
            full_output['test']['failure'].append(path_str)
    except Exception as e:
        full_output['test']['failure'].append(path_str)

    try:
        if plum.get_covered_functions():
            full_output['coverage']['success'].append(path_str)
        else:
            full_output['coverage']['failure'].append(path_str)
    except Exception as e:
        full_output['coverage']['failure'].append(path_str)

def summarize_results(full_output):
    """Prints summary of the initialization, testing, and coverage results."""
    init_results = full_output['repo_init']
    test_results = full_output['test']
    coverage_results = full_output['coverage']

    print(f"Initialization - Success: {len(init_results['success'])}, Failure: {len(init_results['failure'])}")
    print(f"Testing - Success: {len(test_results['success'])}, Failure: {len(test_results['failure'])}")
    print(f"Coverage - Success: {len(coverage_results['success'])}, Failure: {len(coverage_results['failure'])}")

if __name__ == '__main__':
    main()
