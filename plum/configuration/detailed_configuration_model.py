from pydantic import BaseModel, field_validator, HttpUrl, StringConstraints
from typing import Dict, Literal, Optional
from typing_extensions import Annotated
from plum.utils.logger import Logger

class DetailedRepository(BaseModel):
    """A detailed representation of a Git repository.
    Contains the URL, commit hash, and local directory to store the files in."""
    url: HttpUrl
    """URL of the Git repository"""
    commit: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^[0-9a-f]{40}$')]
    """Commit hash of the repository"""
    local_dir: str
    """Local location of the repository. Relative to the root of the PLUM project."""

class EnvironmentConfig(BaseModel):
    type: Literal['docker']
    """Type of environment. Currently only supports Docker."""
    image: str
    """Docker image to use"""
    tag: str
    """Tag of the Docker image"""
    work_dir: str
    """Working directory of the Docker image"""

class KnownRepositoryDetails(BaseModel):
    repo: DetailedRepository

    env: Optional[EnvironmentConfig]
    """
    Environment configuration for the repository.
    Only populated when the repo is built at least once.
    """

class DetailedConfiguration(BaseModel):
    groups: Dict[str, Dict[str, KnownRepositoryDetails]]
    """Dictionary of groups, where each group is a dictionary of repositories.
    Guaranteed to have a 'default' group."""

    @field_validator('groups')
    def validate_groups(cls, v):
        """Ensure that the 'default' group is present."""
        if 'default' not in v:
            raise ValueError("A 'default' group is required")
        return v

if __name__ == "__main__":
    # Example JSON
    example_json = {
        "groups": {
            "default": {
                "FloatingMilkshake--MechanicalMilkshake--b15a1c": {
                    "repo": {
                        "url": "https://github.com/FloatingMilkshake/MechanicalMilkshake",
                        "commit": "b15a1c71eca6be90a2b4f92ed216e2d5aef56c89",
                        "local_dir": "FloatingMilkshake--MechanicalMilkshake--b15a1c"
                    },
                    "env": {
                        "type": "docker",
                        "image": "mcr.microsoft.com/dotnet/sdk",
                        "tag": "5.0",
                        "work_dir": "/app"
                    }
                },
                "FloatingMilkshake--MechanicalMilkshake--be5c08": {
                    "repo": {
                        "url": "https://github.com/FloatingMilkshake/MechanicalMilkshake",
                        "commit": "be5c082041391c463fb207727edeff2547663178",
                        "local_dir": "FloatingMilkshake--MechanicalMilkshake--be5c08"
                    },
                    "env": {
                        "type": "docker",
                        "image": "mcr.microsoft.com/dotnet/sdk",
                        "tag": "6.0",
                        "work_dir": "/app"
                    }
                }
            }
        }
    }


    config = DetailedConfiguration(**example_json)
    Logger().get_logger().info(config)

    Logger().get_logger().info(DetailedConfiguration.model_json_schema())
