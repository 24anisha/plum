import click

from plum.cli.plum_state import PlumState

@click.command()
def init():
    """Initialize data in the current working directory."""
    PlumState().init()

    print("Initialized empty Plum project.")
