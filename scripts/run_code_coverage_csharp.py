import argparse
import time


from plum.environments.csharp_repo import CsharpRepository
from plum.actions.csharp_dotnet_actions import CsharpDotnetActions


def get_args_parser():
    parser = argparse.ArgumentParser(description="Build and run code coverage on a specified C# repository.")
    parser.add_argument(
        "repo_path",
        type=str,
        help="Path to the C# repository."
    )
    parser.add_argument(
        "--docker_image",
        type=str,
        default="mcr.microsoft.com/dotnet/sdk",
        help="Docker image to use."
    )
    parser.add_argument(
        "--docker_tag",
        type=str,
        default="8.0",
        help="Docker tag to use."
    )
    return parser

def get_repo_coverage(repo_path, docker_image, docker_tag):
    """
    Build the C# repository at the specified path and return the result.
    """
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

    if coverage_res.get("success", "") == False:
        raise Exception("Failed to generate coverage report.")

    covered_fx = {
        module_path:csharp_actions.get_covered_functions(report) for module_path, report in coverage_res.items()
    }
    coverage_duration = time.time() - start_time

    return {
        "repo": repo_path,
        "build_result": build_result,
        "build_duration": build_duration,
        "coverage_result": coverage_res,
        "coverage_duration": coverage_duration,
        "covered_functions": covered_fx
    }

def main(repo_path, docker_image, docker_tag):
    result = get_repo_coverage(repo_path, docker_image, docker_tag)
    print(f"Build Result: {result['build_result']['status_result']}")
    print(f"Build Duration: {result['build_duration']}")
    # print(f"Coverage Result: {result['coverage_result']}")
    print(f"Coverage Duration: {result['coverage_duration']}")

    sum = 0
    print("\n==Coverage Results:")
    for module, covered_functions in result['covered_functions'].items():
        sum += len(covered_functions)
        print(f"{module}: {len(covered_functions)}")
    print(f"Total Covered Functions: {sum}")

if __name__ == "__main__":
    args = get_args_parser().parse_args()

    start_time = time.time()
    try:
        main(args.repo_path, args.docker_image, args.docker_tag)
    except Exception as e:
        print("Failed due to: ", e)
    finally:
        print("--- %s seconds ---" % (time.time() - start_time))
