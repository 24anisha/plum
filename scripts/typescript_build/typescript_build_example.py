import argparse
import json
from pathlib import Path
from loguru import logger

from plum.testgen.ts_testgen import TSTestCodeGenerator, TSCodeTranslator


def main():
    parser = argparse.ArgumentParser(
        description='Process arguments for code generation experiment')
    parser.add_argument("-b",
                        "--base",
                        type=str,
                        help="base path for the repo",
                        required=True)
    parser.add_argument("-r",
                        "--repo_path",
                        type=str,
                        help="owner/repo_name for the github repo",
                        required=True)
    args = parser.parse_args()

    build_example(args)


def build_example(args):

    code_generator = TSTestCodeGenerator(args.base, args.repo_path)
    code_generator.setup(clone_repo=True, cleanup=True)

    project_dir = code_generator.repo.clone_path

    # insert a bug in the code
    Path(project_dir.joinpath("src")).mkdir(parents=True, exist_ok=True)
    with project_dir.joinpath("src/error.ts").open("w") as f:
        code_with_bug = f"""
        var a = 1;
        c = a + b;
        """
        f.write(code_with_bug)

    parsed_output = code_generator.build()

    logger.info(f"parsed_output: {parsed_output}")

    with Path("parsed_output.json").open("w") as f:
        json.dump(parsed_output, f, indent=4)

    logger.info(f"Saved to parsed_output.json")


if __name__ == "__main__":
    main()
