import argparse
import json
import logging
import os
import glob
import time
from tqdm import tqdm
from multiprocessing import cpu_count, Pool


from plum.environments.csharp_repo import CsharpRepository
from plum.actions.csharp_dotnet_actions import CsharpDotnetActions


def get_args_parser():
    parser = argparse.ArgumentParser(description="Build C# repositories in a directory.")

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
        default="build_report.jsonl",
        help="Path to the output file."
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="ERROR",
        choices=["NONE", "ERROR", "INFO", "DEBUG"],
        help="Set verbosity level (NONE, ERROR, INFO, DEBUG)"
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


def split_repo_path(repo_path):
    # Sterilize the path string
    sterilized_path = repo_path.replace('\\', '/')

    # Split the path by slashes
    split_path = sterilized_path.split('/')

    # Extract the last directory
    subdirectory = split_path[-1]

    # Extract the remaining prefix
    prefix = '/'.join(split_path[:-1])

    return prefix, subdirectory

def build_repo(repo_path):
    """
    Build the C# repository at the specified path and return the result.
    """
    # C# actions require a base directory and the subdirectory. Split the repo_path.
    base, repo_subdir = split_repo_path(repo_path)

    repo = CsharpRepository(base, repo_subdir)
    repo.repo_init(False)

    csharp_actions = CsharpDotnetActions(
        environment=repo,
        docker_image="mcr.microsoft.com/dotnet/sdk",
        docker_tag="6.0",
    )

    start_time = time.time()
    result = csharp_actions.build()
    duration = time.time() - start_time
    return {
        "repo": repo_path,
        "success": result["status_result"] == "SUCCESS",
        "duration": duration,
        "stdout": result["stdout"],
        "stderr": result["stderr"]
    }

def write_result_to_file(result, file):
    """
    Write the build result to a JSONL file.
    """
    json_record = json.dumps(result)
    file.write(json_record + "\n")

def main(
        input_dir: str,
        use_multiprocessing: bool,
        repo_limit: int,
        output_file: str,
    ):
    print(
        f"Building C# repositories in {input_dir}. "
        f"{'Not using' if not use_multiprocessing else 'Using'} multiprocessing. "
        f"Output file: {output_file}"
    )
    subdirs = [d for d in glob.glob(os.path.join(input_dir, '*/')) if os.path.isdir(d)]

    # Apply the repository limit if specified
    if repo_limit is not None and repo_limit > 0:
        subdirs = subdirs[:repo_limit]
        print(f"Limiting to {repo_limit} repositories.")


    results = []
    with open(output_file, "w") as file:
        if use_multiprocessing:
            # Determine the number of processes.
            # We want to use as many processes as necessary, but not more than 60.
            # Python's multiprocessing library has innate problems on Windows.
            # We also leave 1 thread for OS processes.
            num_processes = min(cpu_count() - 1, len(subdirs), 60)

            with Pool(processes=num_processes) as pool:
                for result in tqdm(pool.imap_unordered(build_repo, subdirs), total=len(subdirs)):
                    write_result_to_file(result, file)
                    results.append(result)
        else:
            for d in tqdm(subdirs):
                result = build_repo(d)
                write_result_to_file(result, file)
                results.append(result)

    # Summary logic
    total_repos = len(results)
    successful_repos = sum(1 for result in results if result['success'])
    success_rate = successful_repos / total_repos if total_repos > 0 else 0
    average_duration = sum(result['duration'] for result in results) / total_repos if total_repos > 0 else 0

    print("Summary Report:")
    print(f"Total Repositories Processed: {total_repos}")
    print(f"Successful Builds: {successful_repos}")
    print(f"Success Rate: {success_rate:.2f}")
    print(f"Average Build Duration: {average_duration:.2f} seconds")

    print(f"Detailed logs output to: {output_file}")

if __name__ == "__main__":
    args = get_args_parser().parse_args()

    configure_logging(args.log_level)

    start_time = time.time()
    try:
        main(args.input_dir, args.multiprocess, args.limit, args.output_file)
    except Exception as e:
        print("Failed due to: ", e)
    finally:
        print("--- %s seconds ---" % (time.time() - start_time))
