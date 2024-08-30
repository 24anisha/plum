import json
from pathlib import Path
from dataclasses import dataclass
import os
import openai
import re
import argparse

from plum.testgen.ts_testgen import TSTestCodeGenerator
from plum.testgen.python_testgen import PythonTestCodeGenerator
from plum.utils.prompt_creation import (
    PromptCreation,
    FocalMethod,
    Docstring,
    GenerationPrefix,
)
from plum.utils.helpers import (
    format_plum_results,
    pass_at_k
)

def main():
    parser = argparse.ArgumentParser(description='Process arguments for code generation experiment')
    parser.add_argument("-b", "--base", type=str, help="base path for the repo", required=True)
    parser.add_argument("-r", "--repo_path", type=str, help="owner/repo_name for the github repo", required=True)
    args = parser.parse_args()
    run_experiment(args)

def run_experiment(args):

    results = {}
    # code_generator = PythonTestCodeGenerator(args.base, args.repo_path)
    code_generator = TSTestCodeGenerator(args.base, args.repo_path)
    code_generator.setup(clone_repo=True, cleanup=True)
    functions = code_generator.get_functions()
    completion_args = {
        "engine": "athena-code-davinci-002", 
        "temperature": 0.1, 
        "max_tokens": 200, 
        "top_p": 0.95, 
        "frequency_penalty": 0, 
        "presence_penalty": 0, 
        "stop": None,
        "n": 1,
        "k": 1
    }

    for fnhash in functions:
        function = functions[fnhash]
        # use the function object to gain information about a given function
        if function.name in code_generator.ignore_functions:
            continue

        prompt = code_generator.make_prompt(fnhash)

        """
        alternatively, you can manually create a prompt
        to your specifications using the PromptCreation class

        prompt_pieces = []
        # prompt_pieces.append(Comment("function.js", self.language))
        focal_method_string = self.make_function(function_name)
        prompt_pieces.append(FocalMethod(focal_method_string))
        prompt_pieces.append(
            Docstring(
                "What follows is a Javascript Mocha and Chai unit test of the above code",
                self.language,
            )
        )
        prompt_pieces.append(GenerationPrefix(self.prompt_suffix))
        prompt = PromptCreation(prompt_pieces).prompt
        """
        completion_args["source"] = prompt
        obj, completions = code_generator.get_completion(fnhash, completion_args)

        full_test_strings = code_generator.format_tests(completions)
        code_generator.save_generated_tests(fnhash, full_test_strings)
        fn_results = code_generator.evaluate_tests(fnhash, full_test_strings)

        # pass@k functionality
        pass_at_k_stat = pass_at_k(completion_args["n"], completion_args["k"], fn_results)
        results[fnhash] = (fn_results, pass_at_k_stat)

    print(results)
    # format_plum_results(results)

if __name__ == "__main__":
    main()
