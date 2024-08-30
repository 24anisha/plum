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
from plum.utils.prompt import PYTHON_PROMPT


def main():
    parser = argparse.ArgumentParser(description='Process arguments for code generation experiment')
    parser.add_argument("-b", "--base", type=str, help="base path for the repo", required=True)
    parser.add_argument("-r", "--repo-list", type=str, help="path to the list of repos", required=True)
    parser.add_argument("-s", "--hashes", type=str, help="path to the list of hashes", required=True)
    parser.add_argument("-e", "--experiment-name", type=str, help="name of the experiment", required=True)
    args = parser.parse_args()

    # read the repo list
    repo_names = pd.read_csv(args.repo_list).repo_name.apply(lambda x: x.strip().replace("/", "--")).tolist()
    hashes = set(line.strip() for line in open(args.hashes))

    output_path = f"experiments/{args.experiment_name}.jsonl"
    if os.path.exists(output_path):
        os.remove(output_path)
    
    for repo_name in tqdm(repo_names):
        run_experiment(args.base, repo_name, hashes, output_path)


def run_experiment(base, repo_name, hashes, output_path):
    results = {}
    self = PythonTestCodeGenerator(base, repo_name)
    methods = self.get_functions()
    for fnhash, method in methods.items():
        obj = {}
        obj["hash"] = fnhash
        if fnhash not in hashes:
            continue
        # obj["method"] = method
        obj["file"] = {
            "relative_path": method.relative_path,
            "repo_name": repo_name,
        }
        
        if method.class_info["original_string"]:
            method_definition = method.class_info["original_string"]
        else:
            method_definition = method.original_string

            
        obj["prompt"] = PYTHON_PROMPT.format(
            imports=method.imports,
            language="python",
            name=method.name,
            importline=method.import_line,
            method_definition=method_definition,
        )
        
        obj["completion"] = ""
        
        write_data_jsonl(obj, output_path)

if __name__ == "__main__":
    main()


