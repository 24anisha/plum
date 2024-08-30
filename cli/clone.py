import click
from os import getcwd

from plum.cli.plum_clone import PlumClone

@click.command()
@click.argument('groups', nargs=-1, default=None)
@click.option('--multiprocessing/--no-multiprocessing', 'use_multiprocessing', default=True, help='Enable or disable multiprocessing.')
@click.option('--limit', default=None, type=int, help='Limit the number of items to process.')
@click.option('--quiet', is_flag=True, help='Run in quiet mode without printing progress.')
def clone(groups, use_multiprocessing, limit, quiet):
    """
    Clones specified group or groups from the Plum configuration file.
    """
    cloner = PlumClone(getcwd(), groups, use_multiprocessing, limit)
    cloner.run(quiet)
