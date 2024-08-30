import json
from pathlib import Path
from dataclasses import dataclass
import os
import openai
import re
import argparse

import pandas as pd
from tqdm import tqdm

from plum.testgen.js_testgen import JSTestCodeGenerator
from plum.testgen.python_testgen import PythonTestCodeGenerator
from plum.utils.helpers import (
    format_plum_results,
    pass_at_k,
    write_data_jsonl
)
from plum.utils.prompt import VSCODE_SYSTEM_PROMPT
from plum.utils.llms import gpt

import ray
ray.init()


def main():
    parser = argparse.ArgumentParser(description='Process arguments for code generation experiment')
    parser.add_argument("-b", "--base", type=str, help="base path for the repo", required=True)
    parser.add_argument("-e", "--experiment-name", type=str, help="name of the experiment", required=True)
    parser.add_argument("-m", "--model-name", type=str, help="name of the model", required=True, choices=["gpt3.5", "gpt4"])
    args = parser.parse_args()

    input_path = f"experiments/{args.experiment_name}-completions-{args.model_name}.jsonl"
    df = pd.read_json(input_path, lines=True)

    output_path = f"experiments/{args.experiment_name}-execution-{args.model_name}.jsonl"
    if os.path.exists(output_path):
        os.remove(output_path)
    
    execution = []
    for index, row in df.iterrows():
        execution.append(execute.remote(row, args.base, output_path))
        # execution.append(execute(row, args.base, output_path))
    ray.get(execution)
    


@ray.remote
def execute(row, base, output_path):
    repo_name = row["file"]["repo_name"]
    self = PythonTestCodeGenerator(base, repo_name)

    completion = row["completion"]
    if not completion:
        return
    completion = self.postprocess(completion)

    fnhash = row["hash"]
    test_file = self.save_generated_test(completion, fnhash)

    # TODO: this is a hack, get the function name eventually
    function_name = fnhash.split("--")[0]
    result = self.execute_test_file(function_name, test_file)

    self.delete_generated_file(test_file)

    row["success"] = result["success"]
    row["stdout"] = result["stdout"]
    row["stderr"] = result["stderr"]

    write_data_jsonl(row.to_dict(), output_path)


if __name__ == "__main__":
    main()


