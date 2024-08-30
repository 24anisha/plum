import sys
import os
import openai
import json
from pathlib import Path
from random import sample
import backoff
from openai.error import RateLimitError
from tenacity import retry, stop_after_attempt, wait_random_exponential
from plum.utils.logger import Logger


@backoff.on_exception(backoff.expo, RateLimitError)
def gpt(prompt, system, model="gpt4"):
    openai.api_type = "azure"
    openai.api_base = "https://inferenceendpointeastus.openai.azure.com/"
    openai.api_version = "2023-03-15-preview"
    # openai.api_base = "https://inferenceendpoint0.openai.azure.com/"
    # openai.api_version = "2022-12-01"

    openai.api_key = os.environ.get("OPENAI_API_KEY")

    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

    if model == "gpt4":
        engine="athena-gpt-4"
    elif model == "gpt3.5":
        engine="athena-gpt-35-turbo"
    else:
        raise Exception("Invalid model")

    try:
        completion = openai.ChatCompletion.create(
            engine=engine,
            messages=messages,
            temperature=0.3,
            # max_tokens=1000,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
        )["choices"][0]["message"]["content"]
    except Exception as e:
        Logger().get_logger().exception(e)
        completion = "Model Exception"
    
    return completion


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def nonchat_gpt(prompt):
    """
    Intermediate function to get completion using 
    tenacity library rate limiting
    """

    openai.api_type = "azure"
    openai.api_base = "https://inferenceendpoint0.openai.azure.com/"
    # openai.api_base = "https://inferenceendpointeastus.openai.azure.com/"
    openai.api_version = "2022-12-01"

    openai.api_key = os.environ.get("OPENAI_API_KEY")

    request_args = {
        "engine": "athena-gpt-35-turbo", 
        "temperature": 0.1, 
        "max_tokens": 2000, 
        "top_p": 0.95, 
        "frequency_penalty": 0, 
        "presence_penalty": 0, 
        "stop": ["<|im_end|>"],
        "n": 1,
        "k": 1
    }

    response = openai.Completion.create(
        engine=request_args["engine"],
        prompt=prompt,
        temperature=request_args["temperature"],
        max_tokens=request_args["max_tokens"],
        top_p=request_args["top_p"],
        frequency_penalty=request_args["frequency_penalty"],
        presence_penalty=request_args["presence_penalty"],
        stop=request_args["stop"]
    )
    return response.choices[0]['text']
