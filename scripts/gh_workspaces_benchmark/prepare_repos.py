import click


from scripts.gh_workspaces_benchmark._work_paths import (
    get_default_repo_directory,
    get_default_repo_list_path
)
from plum.cli.plum_state import PlumState
from plum.cli.plum_clone import PlumClone


@click.command()
@click.option('--repo-list', default=get_default_repo_list_path(),
              help='Path to the repository list file.')
@click.option('--repo-directory', default=get_default_repo_directory(),
              help='Path to the working directory where repositories will be managed.')
@click.option('--no-clone', is_flag=True, default=False,
              help='Flag to disable cloning of repositories.')
def main(repo_list, repo_directory, no_clone):
    # Read repositories from the file
    with open(repo_list, 'r') as f:
        lines = f.readlines()

    # Initialize the PlumState with the given working directory
    state = PlumState(repo_directory)
    state.init()

    num_added = 0
    # Iterate through each repository in the file
    for line in lines:
        repo = line.strip()
        if not repo:  # Skip empty lines
            continue

        # Add the repository to PlumState
        try:
            state.add(
                group="default",
                git_url=f"https://github.com/{repo}"
            )
            num_added += 1
        except Exception as e:
            print(f"Failed to add repository {repo}: {e}")

    print(f"Added {num_added} repositories to PlumState.")

    # Clone the repositories
    if not no_clone:
        clone = PlumClone(repo_directory)
        clone.run()
    else:
        print(f"Skipping cloning of repositories. "
              "You can use `plum clone` in the working directory to clone them.")

if __name__ == '__main__':
    main()
