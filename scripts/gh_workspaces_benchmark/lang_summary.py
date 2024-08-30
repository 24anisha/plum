import click
from collections import Counter

from scripts.gh_workspaces_benchmark._work_paths import get_default_lang_list_path

@click.command()
@click.option('--input-file', default=get_default_lang_list_path(),
              help='Path to the input file containing repository and language data.')
def analyze_languages(input_file):
    # Read the directory names from the input file
    with open(input_file, "r") as file:
        langs = [line.strip().split(',')[1] for line in file if line.strip()]

    # Extract languages and compute their frequency
    lang_count = Counter(langs)

    # Print the count of each language
    for lang, count in lang_count.items():
        print(f"{lang}: {count}")

if __name__ == '__main__':
    analyze_languages()
