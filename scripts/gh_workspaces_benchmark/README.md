# GitHub Workspaces
The scripts of this folder exist to perform a benchmark for our collaboration with GitHub Next. These scripts allow us to run PLUM on a given list of repositories to check our functionality on the repos.

# How to Run
There exist a few scripts that need be run in order. Refer to each script for more detailed configuration.

1. `python prepare_repos.py`: Given the raw list of repos, clones them all to a specified directory.
2. `python build_test_list.py`: On locally cloned repos, runs PLUM and generates a JSON report of the outcome.
3. `python summarized_results.py`: Using the JSON report, generate a summarized report.
4. `python lang_summary.py`: Simply count how many repos exist per language.
