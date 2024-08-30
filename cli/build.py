import click
from os import getcwd


from plum.cli.plum_build import PlumBuild


@click.command()
@click.option('--lang', type=click.Choice(['cpp', 'csharp', 'java', 'javascript', 'python', 'typescript'], case_sensitive=False), required=True, help='Programming language.')
@click.option('--multiprocessing/--no-multiprocessing', default=True, help='Enable or disable multiprocessing.')
@click.argument('dir', required=False, type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True)) # help="Specify only when building a single directory."
def build(lang, multiprocessing, dir):
    """Build operations for specified language."""
    if dir:
        # Build for the specified directory
        print(
            f"Building single {lang} project in directory: {dir}. "
            f"{'Not using' if not multiprocessing else 'Using'} multiprocessing."
        )
    else:
        # If no directory is specified, build for each subdirectory in CWD
        print(
            f"Building all {lang} projects in the current working directory: {getcwd()}. "
            f"{'Not using' if not multiprocessing else 'Using'} multiprocessing."
        )

    # Create an instance of PlumBuild with the provided language and multiprocessing flag
    plum_build = PlumBuild(lang, multiprocessing, working_directory=getcwd(), specific_subdir=dir)

    # Run the build process
    plum_build.run()
