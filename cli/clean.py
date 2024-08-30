import click
from os import getcwd
from plum.cli.plum_clean import PlumClean

@click.command()
@click.option('--lang', type=click.Choice(['cpp', 'csharp', 'java', 'javascript', 'python', 'typescript'], case_sensitive=False), required=True, help='Programming language.')
@click.option('--full-clean', is_flag=True, default=False, help='Whether to perform a full removal of the directory and not just an artifacts clean up.')
@click.option('--multiprocessing/--no-multiprocessing', default=True, help='Enable or disable multiprocessing.')
@click.option('--quiet', is_flag=True, default=False, help='Whether to suppress output.')
@click.argument('dir', required=False, type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True)) # help="Specify only when cleaning a single directory."
def clean(lang, full_clean, multiprocessing, quiet, dir):
    """Clean operations for the Plum project."""
    if dir:
        # Clean for the specified directory
        print(
            f"Cleaning single project in directory: {dir}. "
        )
    else:
        # If no directory is specified, clean for each subdirectory in CWD
        print(
            f"Cleaning all projects in the current working directory: {getcwd()}. "
        )

    # Create an instance of PlumClean with the provided full_clean flag
    plum_clean = PlumClean(
        lang=lang,
        multiprocessing=multiprocessing,
        working_directory=getcwd() if dir is None else dir,
        full_clean=full_clean
    )

    # Run the clean process
    plum_clean.run(quiet=quiet)
