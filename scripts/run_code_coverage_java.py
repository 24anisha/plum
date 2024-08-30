import argparse
import time


from plum.environments.java_repo import JavaRepository
from plum.actions.java_mvn_actions import JavaMavenActions


def get_args_parser():
    parser = argparse.ArgumentParser(description="Build and run code coverage on a specified Java repository.")
    parser.add_argument(
        "repo_path",
        type=str,
        help="Path to the Java repository."
    )
    parser.add_argument(
        "--docker_image",
        type=str,
        default="maven",
        help="Docker image to use."
    )
    parser.add_argument(
        "--docker_tag",
        type=str,
        default="3.3-jdk-8",
        help="Docker tag to use."
    )
    return parser

def get_repo_coverage(repo_path, docker_image, docker_tag):
    """
    Build the Java repository at the specified path and return the result.
    """
    repo = JavaRepository(repo_path, "")
    repo.setup()

    java_actions = JavaMavenActions(
        environment=repo,
        docker_image=docker_image,
        docker_tag=docker_tag,
        local_repository=repo_path
    )
    build_result = java_actions.build()

    coverage_res = java_actions.get_coverage()

    if coverage_res.get("success", "") == False:
        raise Exception("Failed to generate coverage report.")

    covered_fx = {
        module_path:java_actions.get_covered_functions(report) for module_path, report in coverage_res.items()
    }

    return {
        "build_result": build_result,
        "coverage_result": coverage_res,
        "covered_functions": covered_fx
    }

def main(repo_path, docker_image, docker_tag):
    result = get_repo_coverage(repo_path, docker_image, docker_tag)
    print(f"Build successful: {result['build_result']}")
    print(f"Coverage Result: {result['coverage_result']}")

    sum = 0
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
