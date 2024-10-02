from plum.environments.py_repo import PythonRepository
from plum.environments.js_repo import JavascriptRepository
from plum.actions.py_actions import PythonActions
from plum.actions.js_actions import JavascriptActions

from plum.actions import Actions
from plum.environments import Repository
import click


@click.command()
@click.option('--base', help='Base path at which to clone the git repo')
@click.option('--repo_path', help='"username/reponame"')
def run_one_repo(base, repo_path):
    repo = Repository("Python", base, repo_path)
    repo.setup(cleanup=True)
    functions = repo.get_functions()
    print(functions)
    actions = Actions("python", repo)
    covered_functions = actions.get_covered_functions()

    control_test_report = actions.run_test_suite()
    print(control_test_report)

def main():
    run_one_repo()

if __name__ == "__main__":
    main()
