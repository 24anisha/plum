import click
from os import getcwd

from plum.cli.plum_coverage import PlumCoverage

@click.command()
@click.option('--lang', type=click.Choice(['cpp', 'csharp', 'java', 'javascript', 'python', 'typescript'], case_sensitive=False), required=True, help='Programming language.')
@click.option('--multiprocessing/--no-multiprocessing', default=True, help='Enable or disable multiprocessing.')
@click.argument('dir', required=False, type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True)) # help="Specify only when building a single directory."
def coverage(lang, multiprocessing, dir):
    """Coverage operations."""
    if dir:
        # Build for the specified directory
        print(
            f"Generating coverage report for single {lang} project in directory: {dir}. "
            f"No multiprocessing for processing single directory."
        )
        multiprocessing = False
    else:
        # If no directory is specified, build for each subdirectory in CWD
        print(
            f"Generating coverage reports for all {lang} projects in the current working directory: {getcwd()}. "
            f"{'Not using' if not multiprocessing else 'Using'} multiprocessing."
        )

    plum = PlumCoverage(lang, multiprocessing, working_directory=getcwd(), specific_subdir=dir)
    plum.run()
