# Full Docker Process Instructions #
## Set Up plum-api ##
Clone the plum-api repo

## Set Up Dockerfile ##
In order to install the necessary python packages, you will need an access token for the internal python package 
index for DevDiv. You can get a personal access token [here](https://dev.azure.com/DevDiv-Data-AI/_usersSettings/tokens)

Once you've gotten a personal access token, uncomment line 52 of the Dockerfile and paste your access token in.
Then, run the following commands:
```
docker build . -t plum-image
docker run -it --rm --entrypoint bash --name plum -v [PATH_TO_PLUM]:/data/plum-api plum-image
```

where `PATH_TO_PLUM` is your local path to the plum-api directory

Inside the docker image, set up your OpenAI API Key:
`export OPENAI_API_KEY=[API_KEY]`

where `API_KEY` is your OpenAI API Key. 

## Running plum_docker.py in Docker ##
```
cd /data/plum-api/
mkdir cloned_repos
cd scripts/docker_process
python plum_docker.py --base /data/plum-api/cloned_repos --repo_file [REPO_FILE]  --lang [LANG]
```

`BASE_PATH` is where the repos will be cloned. 

`REPO_FILE` is the path to a newline-separated txt file with a list of github repos in the form 'owner_name/repo_name'.
- This flag is optional, and if you don't input a file it will iterate over the list `repos`, as defined on line 174 of plum_docker.py 
- An example input file to use for Python repos can be found at `plum-api/plum/data/10k_challenge_fns_py.csv`.

`LANG` is 'py', 'js' or 'ts', depending on the language of the repos you are processing.

## Running end_to_end.py in Docker ##

```
cd /data/plum-api/
mkdir cloned_repos
cd scripts/docker_process
python end_to_end.py -b /data/plum-api/cloned_repos
```

`BASE_PATH` is where the repos will be cloned. 
In end_to_end.py, there is only one python repo to serve as an example of how the process looks.














## Results ##
This process should result in a JSONL file for each repo at path `BASE_PATH/owner_name--repo_name.JSONL`, where each line in each JSONL file contains information about 
one focal method and its respective generated and evaluated test. The structure of each line of this JSONL file can be seen in the `build_data` function
of `docker_plum.py`.

## Note ##
Sometimes, this process fails quietly if OpenAI performs rate limiting. In stdout, you should see:
- `====Prompt====`, followed by the prompt passed to the OpenAI API
- `====Generation====`, followed by unit test code.

for every focal method in the repo. 

I am working on making this return a stacktrace (or not fail at all).
