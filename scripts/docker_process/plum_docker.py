from multiprocessing import Process, cpu_count
from multiprocessing.dummy import Pool
import json
from pathlib import Path
import os
import time
import argparse
import subprocess

from random import sample 

from plum.harnesslib.languages import Language
from plum.testgen.js_testgen import JSTestCodeGenerator
from plum.testgen.python_testgen import PythonTestCodeGenerator
# from prompt_helpers import parse_prompts


def parse_prompts(prompts_jsonl):
    """
    TODO EVENTUALLY
    Take in JSONL file with prompts and munge a dict 
    with {repo : {method: prompt, method: prompt}}

    Once implemented, put this function in the prompt_helpers file 
    with any other helper functions for prompt handling
    """
    raise NotImplementedError("Passing in pre-generated prompts has not been implemented yet")


def write_data_jsonl(datapoints, writepath):
    """
    Writes the data for each focal method from one repo 
    to a jsonl file (one file for each repo). This jsonl
    file contains the text of all the generated tests, as well
    as the evaluation of each test (NOTE: evaluation for python is currently not correct)
    """

    with open(writepath, 'w', encoding='utf-8') as f:
        for d in datapoints:
            json.dump(d, f, ensure_ascii=False)
            f.write('\n')


def build_data(code_generator, function, engine):   
    """
    Builds the datapoint scaffold for a given function
    """
    data_point = {}
    method = function.function_dict
    data_point['method'] = method

    file_info = {
        "relative_path": str(method["relative_path"]),
        "file_hash": "",
        "url": f"https:/github.com/{code_generator.repo_path}",
        "repo_name": str(code_generator.repo_path),
        "commit_hash": code_generator.commit_sha
    }
    # TODO implement original_string access for focal file for python

    data_point['file'] = file_info

    data_point["prompt"] = ""
    data_point["completion"] = ""
    data_point["evaluation"] = ""

    return data_point


def build_eval_json(fnhash, fn_results):
    """
    Build the evaluation json data to be added to the method datapoint
    NOTE: Currently, the TestResult key is incorrect. It runs the test within
    its own file, but we have an alternative process for running tests
    (I will update this accordingly once Shubham tells me how he evaluates tests)
    """

    for i in range(len(fn_results)):
        result = fn_results[i]
        eval_dict = {
            "FocalMethodId": fnhash,
            "TestCaseId": i,
            "TestRun": "precheck_error: " not in result['stderr'],
            "Output": {
                "stdout": result['stdout'],
                "stderr": result['stderr'],
            },
            "TestResult": result['success']
        }

        return eval_dict


def single_fn(function, fnhash, code_generator, completion_args, input_dict):
    """
    For a given function:
        - make prompt
        - build method datapoint scaffold
        - get completion from model
        - write generated test to file
        - evaluate generation
    
    Returns:
        method datapoint
    """

    if function.name not in code_generator.ignore_functions:
        
        method_datapoint = build_data(code_generator, function, completion_args['engine'])

        # Here, I use my API to create a prompt to send to the OpenAI API
        # However, in the AML component use case, we may want the user to pass in their prompts.
        # In that workflow, we would search a jsonl of input prompts for the matching method, and set that 
        # as method_datapoint["prompt"]
        if input_dict:
            method_datapoint["prompt"] = input_dict.get(code_generator.repo_path)
        else:
            method_datapoint["prompt"] = code_generator.make_prompt(function, fnhash)
        completion_args["source"] = method_datapoint['prompt']

        obj, completions = code_generator.get_completion(fnhash, completion_args)
        if completions[0].completion == "":
            print("empty return")
        # list (of 1) generated test returned
        full_test_strings = code_generator.format_tests(completions)

        # writes generated tests to the all_generated directory within the cloned focal repo
        test_path = code_generator.save_generated_tests(fnhash, full_test_strings)
        fn_result = code_generator.evaluate_test_file(function.name, test_path)        
        # remove generated test
        code_generator.delete_generated_file(test_path)

        method_datapoint['completion'] = full_test_strings[0]
        method_datapoint['evaluation'] = build_eval_json(fnhash, [fn_result])

        return method_datapoint
    
    return None


def run_one_repo(base, repo, language, input_dict):
    """
    - Make and setup CodeGenerator object (from plum package)
    - Get list of all functions
    - For each function, call single_fn to get generated tests
    - Save results
    """
    if language == "py":
        code_generator = PythonTestCodeGenerator(base, repo)
    elif language == "js":
        code_generator = JSTestCodeGenerator(base, repo, language=Language.Javascript)
    elif language == "ts":
        code_generator = JSTestCodeGenerator(base, repo, language=Language.Typescript)
    
    # clone the repo and install required dependencies for given repo
    code_generator.setup(cleanup=False)

    # parse all the code files in the repo to get information about all functions within the repo
    functions = code_generator.get_functions()
    completion_args = {
        "engine": "athena-gpt-35-turbo",
        "temperature": 0.1, 
        "max_tokens": 1000, 
        "top_p": 0.95, 
        "frequency_penalty": 0, 
        "presence_penalty": 0, 
        "stop": None,
        "n": 1,
        "k": 1
    }
    method_datapoints = []

    # create a method datapoint dictionary for each function in the repo
    for fnhash in functions:
        function = functions[fnhash]
        datapoint = single_fn(function, fnhash, code_generator, completion_args, input_dict)

        method_datapoints.append(datapoint)

    # write all method datapoints for the focal repo to a jsonl file
    write_path = f"{base}/{code_generator.internal_repo_path}.jsonl"
    write_data_jsonl(method_datapoints, write_path)


def main():
    parser = argparse.ArgumentParser(description='Process arguments for parallel code generation experiment')
    parser.add_argument("-b", "--base", type=str, help="base path for the repo", required=False, default="/storage/data/python-unit-test/repos/")
    parser.add_argument("-r", "--repo_file", type=str, help="txt or csv file with list of owner/repo_names to be cloned and parsed")
    parser.add_argument("-l", "--lang", type=str, help="language of the repo: {py, js, ts}", required=False, default="py")
    parser.add_argument('-p', "--prompt_file", type=str, help="JSONL file containing a list of prompts for focal methods", default=None)
    args = parser.parse_args()

    pool = Pool(processes=cpu_count())

    # get list of repos to process
    if args.repo_file is None:
        repos = ['johanrosenkilde/nasty_python']
    else:
        repos = open(args.repo_file).read().splitlines()
        if repos[0] == "repo_name":
            repos = repos[1:]

    # parse the prompt file (if provided)
    input_dict = {}
    if args.prompt_file:
        input_dict = parse_prompts(args.prompt_file)
    
    for repo in repos:
        pool.apply_async(run_one_repo, args=(args.base, repo, args.lang, input_dict))
        # run_one_repo(args.base, repo, args.lang, input_dict)

    pool.close()
    pool.join()



if __name__ == "__main__":
    main()
