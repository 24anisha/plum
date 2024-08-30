import click
from os import getcwd


from plum.cli.plum_parse import PlumParse

@click.command()
def parse():
    """Repository parsing operation."""
    cwd = getcwd()
    """Plum project working directory."""
    print("Parsing repositories in", cwd)
    print("Note that this is a WIP feature and may not work as expected.")

    parser = PlumParse(multiprocessing=True, working_directory=cwd)
    parser.run(quiet=False)
