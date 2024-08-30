# TypeScript Example

build a typescript project and capture the errors in a json

## Quick Start

```bash
python typescript_build_example.py -b ~/desktop/ts-projects -r microsoft/playwright
```

- `-b --base`: base directory where the repo will be placed
- `-r --repo_path`: repo path with the format `name/repo`, such as `microsoft/playwright` and `microsoft/storywright`

it will generate a `parsed_output.json` in the current folder, example is given as follows:

<details>

<summary>parsed output example</summary>

```
{
    "FocalMethodId": 999,
    "TestCaseId": 999,
    "TestEvaluated": true,
    "TestFramework": "TypeScript",
    "BuildError": [
        {
            "ProjectFile": "packages/playwright-core/bundles/utils/src/utilsBundleImpl.ts",
            "Line": "20",
            "Column": "26",
            "Code": "TS7016",
            "Message": "Could not find a declaration file for module 'debug'. '/data3/kefan/desktop/ts-projects/microsoft--playwright/node_modules/debug/src/index.js' implicitly has an 'any' type."
        },
        {
            "ProjectFile": "packages/playwright-core/bundles/utils/src/utilsBundleImpl.ts",
            "Line": "23",
            "Column": "32",
            "Code": "TS2307",
            "Message": "Cannot find module 'proxy-from-env' or its corresponding type declarations."
        },
    ],
    "TestResult": {
        "Success": false,
        "ErrorMessages": "",
        "Duration": 0,
        "Output": null,
        "TestDefinition": {
            "Name": "",
            "Class": "",
            "Storage": "",
            "Type": ""
        }
    }
}
```

</details>

## API Usage

- setup a repo

```python
from pathlib import Path
from plum.testgen.ts_testgen import TSTestCodeGenerator

base = "~/desktop/ts-projects"
repo_path = "microsoft/playwright"
code_generator = TSTestCodeGenerator(base, repo_path)
code_generator.setup(clone_repo=True, cleanup=True)
```

- insert a bug in the code

```python
project_dir = code_generator.repo.clone_path

# insert a bug in the code
Path(project_dir.joinpath("src")).mkdir(parents=True, exist_ok=True)
with project_dir.joinpath("src/error.ts").open("w") as f:
    code_with_bug = f"""
    var a = 1;
    c = a + b;
    """
    f.write(code_with_bug)
```

- build project and capture the output

```python
import json
parsed_output = code_generator.build()
with Path("parsed_output.json").open("w") as f:
    json.dump(parsed_output, f, indent=4)
```