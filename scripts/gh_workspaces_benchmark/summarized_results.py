import click
import json


from scripts.gh_workspaces_benchmark._work_paths import (
    get_default_lang_list_path,
)


@click.command()
@click.option('--repo-file', default=get_default_lang_list_path(),
              help='Path to the file containing repository and language mappings.')
@click.option('--results-json', default="plum_benchmark.json",
              help='Path to the JSON file containing the results of operations.')
def process_files(repo_file, results_json):
    """ Processes the files and prints the summarized results. """
    language_mapping = read_language_mapping(repo_file)
    results = read_results(results_json)
    summary = summarize_results(language_mapping, results)
    print_summary(summary)

def read_language_mapping(filename):
    """ Reads the mapping of repositories to languages. """
    language_mapping = {}
    with open(filename, "r") as file:
        for line in file:
            if line.strip():
                repo, lang = line.strip().split(',')
                repo_formatted = repo.replace('/', '--')
                language_mapping[repo_formatted] = lang
    return language_mapping

def read_results(filename):
    """ Reads the results of repository operations from a JSON file. """
    with open(filename, "r") as file:
        return json.load(file)

def summarize_results(language_mapping, results):
    """ Summarizes results per language. """
    summary = {}
    for lang in set(language_mapping.values()):
        summary[lang] = {
            "repo_init": {"total": 0, "success": 0, "failure": 0},
            "test": {"total": 0, "success": 0, "failure": 0},
            "coverage": {"total": 0, "success": 0, "failure": 0}
        }
    for step, outcomes in results.items():
        for outcome, repos in outcomes.items():
            success = outcome == "success"
            for repo_path in repos:
                repo_name = repo_path.split('/')[5][:-8]  # Extract repo name part from the path
                if repo_name in language_mapping:
                    lang = language_mapping[repo_name]
                    summary[lang][step]["total"] += 1
                    if success:
                        summary[lang][step]["success"] += 1
                    else:
                        summary[lang][step]["failure"] += 1
    for lang, stats in summary.items():
        for step in stats:
            total = stats[step]["total"]
            stats[step]["success_ratio"] = round(stats[step]["success"] / total * 100, 2) if total > 0 else 0
    return summary

def print_summary(summary):
    """ Prints the summary of results in a readable format. """
    for lang, stats in summary.items():
        print(f"Language: {lang}")
        for step, data in stats.items():
            print(f"  {step.capitalize()}:")
            print(f"    Total: {data['total']}")
            print(f"    Success: {data['success']}")
            print(f"    Failure: {data['failure']}")
            print(f"    Success Ratio: {data['success_ratio']}%")
        print()

if __name__ == '__main__':
    process_files()

# # File paths
# repo_file = "repo_with_langs.txt"
# results_file = "output.log"
# repo_file = "js_ts_repos.txt"
# results_file = "js_ts_build.log"
