import argparse
import json
import logging
import os
import glob
import subprocess
import time
from tqdm import tqdm
from multiprocessing import cpu_count, Pool


from plum.environments.csharp_repo import CsharpRepository
from plum.actions.csharp_dotnet_actions import CsharpDotnetActions


def get_args_parser():
    parser = argparse.ArgumentParser(description="Build and run code coverage on C# repositories in a directory.")

    parser.add_argument(
        "--input_dir",
        type=str,
        help="Directory containing C# repositories."
    )
    parser.add_argument(
        "--multiprocess",
        action="store_true",
        help="Enable multiprocessing."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of repositories to process."
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="build_coverage_report.jsonl",
        help="Path to the output file."
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="ERROR",
        choices=["NONE", "ERROR", "INFO", "DEBUG"],
        help="Set verbosity level (NONE, ERROR, INFO, DEBUG)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode where Exceptions are not handled."
    )

    return parser

def configure_logging(verbosity: str):
    """
    Configure logging based on the verbosity level.
    none: No logs, error: Errors only, info: Info, debug: Debug (all logs)
    """
    levels = {
        "NONE": None,
        "ERROR": logging.ERROR,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG  # This is effectively 'all' in standard logging levels
    }
    level = levels.get(verbosity.upper())

    if level is not None:
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=level)
    else:
        logging.disable(logging.CRITICAL)  # Disables all logging

def get_git_origin_url(repo_path):
    try:
        return subprocess.check_output(
            ["git", "-C", repo_path, "config", "--get", "remote.origin.url"],
            stderr=subprocess.STDOUT,
        ).decode().strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get git origin URL: {e.output.decode().strip()}")
        return None

def get_git_commit_id(repo_path):
    try:
        return subprocess.check_output(
            ["git", "-C", repo_path, "rev-parse", "HEAD"],
            stderr=subprocess.STDOUT,
        ).decode().strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get git commit ID: {e.output.decode().strip()}")
        return None

def get_repo_coverage(repo_path, docker_image, docker_tag):
    repo = CsharpRepository(repo_path, "")
    repo.repo_init(False)

    csharp_actions = CsharpDotnetActions(
        environment=repo,
        docker_image=docker_image,
        docker_tag=docker_tag,
    )
    start_time = time.time()
    build_result = csharp_actions.build()
    build_duration = time.time() - start_time

    start_time = time.time()
    coverage_res = csharp_actions.get_coverage()

    coverage_duration = time.time() - start_time

    return {
        "repo": repo_path,
        "build_success": build_result["status_result"] == "SUCCESS",
        "build_duration": build_duration,
        "build_result": build_result,
        "coverage_success": coverage_res["success"],
        "coverage_duration": coverage_duration,
        "coverage_result": coverage_res,
    }

def process_repo(repo_path):
    docker_image = "mcr.microsoft.com/dotnet/sdk"
    docker_tag = "6.0"
    res = get_repo_coverage(repo_path, docker_image, docker_tag)

    git_url = get_git_origin_url(repo_path)
    git_commit_id = get_git_commit_id(repo_path)

    return {
        "git_url": git_url,
        "git_commit_id": git_commit_id,
        "build_success": res["build_success"],
        "build_duration": res["build_duration"],
        "build_result": res["build_result"],
        "coverage_success": res["coverage_success"],
        "coverage_duration": res["coverage_duration"],
        "coverage_result": res["coverage_result"],
    }


def write_result_to_file(result, file):
    json_record = json.dumps(result)
    file.write(json_record + "\n")


def main(input_dir: str, use_multiprocessing: bool, repo_limit: int, output_file: str):
    print(f"Processing C# repositories in {input_dir}. Using multiprocessing: {use_multiprocessing}. Output file: {output_file}")
    subdirs = [d for d in glob.glob(os.path.join(input_dir, '*/')) if os.path.isdir(d)]

    if repo_limit is not None and repo_limit > 0:
        subdirs = subdirs[:repo_limit]
        print(f"Limiting to {repo_limit} repositories.")

    results = []
    with open(output_file, "w") as file:
        if use_multiprocessing:
            num_processes = min(cpu_count() - 1, len(subdirs), 60)
            with Pool(processes=num_processes) as pool:
                for result in tqdm(pool.imap_unordered(process_repo, subdirs), total=len(subdirs)):
                    write_result_to_file(result, file)
                    results.append(result)
        else:
            for d in tqdm(subdirs):
                result = process_repo(d)
                write_result_to_file(result, file)
                results.append(result)

    # 3. Summary logic (modified for build and coverage)
    total_repos = len(results)
    successful_builds = sum(1 for result in results if result['build_success'])
    successful_coverage = sum(1 for result in results if result['coverage_success'])
    build_success_rate = successful_builds / total_repos if total_repos > 0 else 0
    coverage_success_rate = successful_coverage / total_repos if total_repos > 0 else 0

    print("Summary Report:")
    print(f"Total Repositories Processed: {total_repos}")
    print(f"Successful Builds: {successful_builds}")
    print(f"Build Success Rate: {build_success_rate:.2f}")
    print(f"Successful Coverages: {successful_coverage}")
    print(f"Coverage Success Rate: {coverage_success_rate:.2f}")

if __name__ == "__main__":
    args = get_args_parser().parse_args()

    configure_logging(args.log_level)

    start_time = time.time()
    if args.debug:
        main(args.input_dir, args.multiprocess, args.limit, args.output_file)
    else:
        try:
            main(args.input_dir, args.multiprocess, args.limit, args.output_file)
        except Exception as e:
            print("Failed due to: ", e)
        finally:
            print("--- %s seconds ---" % (time.time() - start_time))
