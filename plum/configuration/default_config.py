from plum.configuration.configuration_model import SimplifiedConfiguration
from plum.configuration.detailed_configuration_model import DetailedConfiguration

_DEFAULT_CONFIG = {
  "groups": {
    "default": {}
  }
}

DEFAULT_CONFIG = SimplifiedConfiguration(**_DEFAULT_CONFIG)
"""Default configuration"""
DEFAULT_CONFIG_DETAILS = DetailedConfiguration(**_DEFAULT_CONFIG)
"""Default configuration details"""
