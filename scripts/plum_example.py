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
