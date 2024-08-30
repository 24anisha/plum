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
    parser.add_argument("-m", "--model-name", type=str, help="name of the model", required=True, choices=["gpt3.5", "gpt4"])
    parser.add_argument("-e", "--experiment-name", type=str, help="name of the experiment", required=True)
    args = parser.parse_args()

    input_path = f"experiments/{args.experiment_name}.jsonl"
    df = pd.read_json(input_path, lines=True)

    output_path = f"experiments/{args.experiment_name}-completions-{args.model_name}.jsonl"
    if os.path.exists(output_path):
        os.remove(output_path)
    
    generation = []
    for index, row in df.iterrows():
        generation.append(generate.remote(row, args.model_name, output_path))
    ray.get(generation)
    


@ray.remote
def generate(row, model_name, output_path):
    prompt = row["prompt"]
    completion = gpt(prompt, VSCODE_SYSTEM_PROMPT, model=model_name)
    if completion:
        row["completion"] = completion
        write_data_jsonl(row.to_dict(), output_path)

if __name__ == "__main__":
    main()


