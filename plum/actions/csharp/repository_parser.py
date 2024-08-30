from glob import glob
from json import dumps, load
import os
from pathlib import Path
from typing import Optional, Union

from plum.actions.csharp._sln_parser import Solution

class CSharpRepositoryParser:
    def __init__(self, repo_full_path: Union[Path, str]):
        self.repo_path = repo_full_path
        """Full path to the repo to parse."""
        self.solutions = []
        """Parsed solution file."""
        self.global_json: Optional[dict] = None
        """(Optional) Parsed global.json file."""

    def parse(self):
        """Parse the solution and find all projects."""
        # Find the .sln file.
        sln_files = glob(os.path.join(self.repo_path, '*.sln'))

        if not sln_files:
            raise FileNotFoundError("No .sln file found for code coverage generation.")

        # Parse .sln file and find projects.
        for sln_file in sln_files:
            solution = Solution.from_file(sln_file)
            _ = solution.get_projects()
            self.solutions.append(solution)

        # Check if there is a global.json file.
        global_json_file = os.path.join(self.repo_path, 'global.json')
        if os.path.exists(global_json_file):
            with open(global_json_file, 'r') as f:
                self.global_json = load(f)

    def to_dict(self):
        """Return a dictionary representation of the parsed data."""
        return {
            "global_json": self.global_json,
            "solutions": [s.to_dict() for s in self.solutions]
        }
