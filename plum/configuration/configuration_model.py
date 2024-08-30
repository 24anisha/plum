from pydantic import BaseModel, field_validator, HttpUrl, StringConstraints
from typing import Dict
from typing_extensions import Annotated
from plum.utils.logger import Logger

class SimplifiedRepository(BaseModel):
    """A simplified representation of a Git repository, containing only the URL and commit hash."""
    url: HttpUrl
    """URL of the Git repository"""
    commit: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^[0-9a-f]{40}$')]
    """Commit hash of the repository"""

class SimplifiedConfiguration(BaseModel):
    """Simplified configuration file for PLUM. Only holds the declarations for groups of repositories."""
    groups: Dict[str, Dict[str, SimplifiedRepository]]
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
                    "url": "https://github.com/FloatingMilkshake/MechanicalMilkshake",
                    "commit": "b15a1c71eca6be90a2b4f92ed216e2d5aef56c89"
                },
                "FloatingMilkshake--MechanicalMilkshake--be5c08": {
                    "url": "https://github.com/FloatingMilkshake/MechanicalMilkshake",
                    "commit": "be5c082041391c463fb207727edeff2547663178"
                }
            }
        }
    }

    config = SimplifiedConfiguration(**example_json)
    Logger().get_logger().info(config)

    Logger().get_logger().info(SimplifiedConfiguration.model_json_schema())
