import os
from json import dump, load
from tqdm import tqdm
import click


from scripts.gh_workspaces_benchmark._work_paths import (
    get_default_lang_list_path,
    get_default_repo_directory
)


def get_test_package(package_json_path):
    """
    For use with JS and TS
    Returns the testing framework used in the repo natively
    params:
        package_json_path: path to package.json file
    returns:
        test_framework: name of test framework used
        (currently supported options are mocha and jest)
    """
    with open(package_json_path, "r") as package:
        pkg_dict = load(package)

    if 'scripts' in pkg_dict and 'test' in pkg_dict['scripts']:
        test_command = pkg_dict['scripts']['test']
        if "mocha" in test_command:
            return "mocha"
        elif "jest" in test_command:
            return "jest"
        else:
            return "UNKNOWN: " + test_command
    else:
        return None


def count_test_frameworks(result_dict):
    # Initialize counts
    counts = {
        'mocha': 0,
        'jest': 0,
        'UNKNOWN': 0,
        'package.json not found': 0,
        'No test script found': 0
    }

    # Iterate through the JSON data and increment counts
    for key, value in result_dict.items():
        if 'mocha' in value:
            counts['mocha'] += 1
        if 'jest' in value:
            counts['jest'] += 1
        if value.startswith('UNKNOWN'):
            counts['UNKNOWN'] += 1
        if 'package.json not found' in value:
            counts['package.json not found'] += 1
        if 'No test script found' in value:
            counts['No test script found'] += 1

    return counts


@click.command()
@click.option('--base_path', default=get_default_repo_directory(), help='Base path for the directories.')
@click.option('--repo_file', default=get_default_lang_list_path(), help='Path to the file listing repositories with their languages.')
@click.option('--result_json', default="test_frameworks.json", help='File to write results to.')
def main(base_path, repo_file, result_json):
    """Run through the specified folder and try to use PLUM on every repository listed to figure out the testing framework."""
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

    # Detailed output initialization
    test_packages = {}

    # Iterate through all folders which are not hidden
    for txt_line in tqdm(txt_lines):
        print(txt_line)
        directory, language = txt_line.split(",")
        matched_dir = find_directory(directory)

        if not matched_dir:
            print(f"Directory starting with {directory} not found.")
            test_packages[directory] = "Directory not found"
            continue

        full_path = os.path.join(base_path, matched_dir)

        # Check that the package.json is there
        package_json_path = os.path.join(full_path, "package.json")
        if not os.path.exists(package_json_path):
            print(f"package.json not found in {full_path}")
            test_packages[directory] = "package.json not found"
            continue

        print(f"Collecting test package from {full_path}")
        try:
            test_package = get_test_package(package_json_path)
            test_packages[directory] = test_package or "No test script found"
        except Exception as e:
            print(f"An error occurred while collecting the test package from {full_path}: {e}")
            test_packages[directory] = str(e)

    with open(result_json, "w") as f:
        dump(test_packages, f, indent=2)

    print(f"Test packages collected for all repositories listed. Results are saved in {result_json}.")

    # Count the test frameworks
    counts = count_test_frameworks(test_packages)
    # Print results
    click.echo(f"Total: {len(test_packages)}")
    for test_type, count in counts.items():
        click.echo(f"{test_type}: {count}")

if __name__ == '__main__':
    main()