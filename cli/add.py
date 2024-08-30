import click

from plum.cli.plum_state import PlumState

@click.command()
@click.option('--group', default='default', help='Group name to add the repository under')
@click.option('--directory', default=None, help='Directory to add to (optional)')
@click.option('-c', '--commit_hash', default=None, help='Commit hash to add, will default to current HEAD (optional)')
@click.argument('git_url')
def add(group, git_url, commit_hash, directory):
    """Add a new entry to the Plum configuration."""
    state_control = PlumState()

    success, msg = state_control.add(group, git_url, commit_hash, directory)
    click.echo(msg)
    exit(0 if success else 1)

@click.command()
@click.argument('jsonl_file', type=click.Path(exists=True, dir_okay=False, readable=True), required=True)
@click.option('--group', default='default', help='Group name to add the repositories under')
@click.option('--git_url_key', default='git_url', help='The key in the JSON object for the Git URL')
@click.option('--commit_hash_key', default='commit_hash', help='The key in the JSON object for the Git commit hash')
def add_bulk_jsonl(group, jsonl_file, git_url_key, commit_hash_key):
    """Add multiple repositories from a JSONL file to the Plum configuration."""
    state_control = PlumState()

    success, msg = state_control.add_jsonl(group, jsonl_file, git_url_key, commit_hash_key)
    click.echo(msg)
    exit(0 if success else 1)

@click.command()
@click.argument('json_file', type=click.Path(exists=True, dir_okay=False, readable=True), required=True)
@click.option('--group', default='default', help='Group name to add the repositories under')
def add_bulk_json(group, json_file):
    """Add multiple repositories from a JSON file to the Plum configuration.
    Expects the file to be a JSON array with nothing but Git URLs."""
    state_control = PlumState()

    success, msg = state_control.add_json_array(group, json_file)
    click.echo(msg)
    exit(0 if success else 1)

