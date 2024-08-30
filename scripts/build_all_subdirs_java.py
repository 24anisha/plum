import argparse
import json
import os
import glob
import time
from multiprocessing import cpu_count, Pool

from plum.environments.java_repo import JavaRepository
from plum.actions.java_mvn_actions import JavaMavenActions


def get_args_parser():
    parser = argparse.ArgumentParser(description="Build Java repositories in a directory.")

    parser.add_argument(
        "--input_dir",
        type=str,
        help="Directory containing Java repositories."
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

    return parser

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
    Build the Java repository at the specified path and return the result.
    """
    base, repo_subdir = split_repo_path(repo_path)

    repo = JavaRepository(base, repo_subdir)
    repo.setup()

    java_actions = JavaMavenActions(
        environment=repo,
        docker_image="maven",
        docker_tag="3.3-jdk-8",
        local_repository=repo_path
    )

    start_time = time.time()
    build_result = java_actions.build()
    duration = time.time() - start_time
    return {
        "repo": repo_path,
        "success": build_result["status_result"] == "SUCCESS",
        "duration": duration,
        "stdout": build_result["stdout"],
        "stderr": build_result["stderr"]
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
        f"Buiding Java repositories in {input_dir}. "
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
                for result in pool.map(build_repo, subdirs):
                    try:
                        write_result_to_file(result, file)
                    except Exception as e:
                        print("Error")
                    results.append(result)
        else:
            for d in subdirs:
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

    start_time = time.time()
    try:
        main(args.input_dir, args.multiprocess, args.limit, args.output_file)
    except Exception as e:
        print("Failed due to: ", e)
    finally:
        print("--- %s seconds ---" % (time.time() - start_time))
