import json
from pathlib import Path
import re
import argparse

import pandas as pd



error_types = [    'AssertionError',     'AttributeError',    'EOFError',    'FloatingPointError',    'GeneratorExit',    'ImportError',    'IndexError',    'KeyError',    'KeyboardInterrupt',    'MemoryError',    'NameError',    'NotImplementedError',    'OSError',    'OverflowError',    'RecursionError',    'ReferenceError',    'RuntimeError',    'StopIteration',    'SyntaxError',    'IndentationError',    'TabError',    'SystemError',    'SystemExit',    'TypeError',    'UnboundLocalError',    'UnicodeError',    'UnicodeEncodeError',    'UnicodeDecodeError',    'UnicodeTranslateError',    'ValueError',    'ZeroDivisionError', 'Connection refused']
def error(x):
    for error in error_types:
        if error in x:
            return error
    return -1




def main():
    parser = argparse.ArgumentParser(description='Process arguments for code generation experiment')
    parser.add_argument("-e", "--experiment-name", type=str, help="name of the experiment", required=True)
    parser.add_argument("-m", "--model-name", type=str, help="name of the model", required=True, choices=["gpt3.5", "gpt4"])
    args = parser.parse_args()

    input_path = f"experiments/{args.experiment_name}-execution-{args.model_name}.jsonl"
    df = pd.read_json(input_path, lines=True)
    df["error"] = df.stdout.apply(error)


    obj = {
        "name": args.experiment_name,
        "model": args.model_name,
        "repos": df.file.apply(lambda x: x["repo_name"]).unique().shape[0],
        "methods": df.shape[0],
        "passing_tests": df[df.success == True].shape[0],
        "pass@1": round(df.success.mean() * 100, 2),
        "syntax_errors": df[df.error == "SyntaxError"].shape[0],
        "syntax_errors_percent": round(df[df.error == "SyntaxError"].shape[0] / df.shape[0] * 100, 2),
        "import_errors": df[df.error == "ImportError"].shape[0],
        "import_errors_percent": round(df[df.error == "ImportError"].shape[0] / df.shape[0] * 100, 2),
        "failing_tests": df[df.error == "AssertionError"].shape[0],
        "failing_tests_percent": round(df[df.error == "AssertionError"].shape[0] / df.shape[0] * 100, 2),
    }

    obj["build_errors"] = obj["methods"] - (obj["import_errors"] + obj["syntax_errors"] + obj["failing_tests"] + obj["passing_tests"])
    obj["build_errors_percent"] = round(obj["build_errors"] / obj["methods"] * 100, 2)

    assert obj["build_errors_percent"] + obj["import_errors_percent"] + obj["syntax_errors_percent"] + obj["failing_tests_percent"] + obj["pass@1"] > 99.9, obj["build_errors_percent"] + obj["import_errors_percent"] + obj["syntax_errors_percent"] + obj["failing_tests_percent"] + obj["pass@1"]

    print(obj)
    output_path = f"experiments/results.jsonl"
    with open(output_path, "a") as f:
        json.dump(obj, f)
        f.write("\n")





if __name__ == "__main__":
    main()


