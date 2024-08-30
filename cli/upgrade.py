import click
from os import getcwd

from plum.cli.plum_build import PlumBuild
from plum.cli.plum_upgrade import PlumUpgrade

@click.command()
@click.option('--lang', type=click.Choice(['cpp', 'csharp', 'java', 'javascript', 'python', 'typescript'], case_sensitive=False), required=True, help='Programming language.')
@click.option('--multiprocessing/--no-multiprocessing', default=True, help='Enable or disable multiprocessing.')
@click.argument('dir', required=False, type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True)) # help="Specify only when upgrading a single directory."
def upgrade(lang, multiprocessing, dir):
    """Upgrade operations for specified language."""
    if dir:
        # Upgrade for the specified directory
        print(
            f"Upgrading single {lang} project in directory: {dir}. "
            f"{'Not using' if not multiprocessing else 'Using'} multiprocessing."
        )
    else:
        # If no directory is specified, upgrade for each subdirectory in CWD
        print(
            f"Upgrading all {lang} projects in the current working directory: {getcwd()}. "
            f"{'Not using' if not multiprocessing else 'Using'} multiprocessing."
        )

    # Create an instance of PlumUpgrade with the provided language and multiprocessing flag
    plum_upgrade = PlumUpgrade(lang, multiprocessing, working_directory=getcwd(), specific_subdir=dir)

    # Run the upgrade process
    plum_upgrade.run()
    print("Upgrade is done. Now running build to verify upgrade")

    # Create an instance of PlumBuild with the provided language and multiprocessing flag to verify upgrade
    plum_build = PlumBuild(lang, multiprocessing, working_directory=getcwd(), specific_subdir=dir)

    # Run the build process
    plum_build.run()
