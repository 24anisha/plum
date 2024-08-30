from pathlib import Path
from types import MappingProxyType
from typing import Union


from plum.utils.cobertura import parse_xml_as_dict
from plum.actions.java.maven._pom_parser_lxml import PomXML


COBERTURA_DETAILS = MappingProxyType(
    {
        "group_id": "org.codehaus.mojo",
        "artifact_id": "cobertura-maven-plugin",
        "version": "2.7"
    }
)
"""Pseudo frozendict containing the details for the Cobertura Maven plugin."""


class CoberturaMavenPlugin:
    """
    Controller class for interacting with the Cobertura Maven plugin.
    """
    def __init__(self, pom_path: Union[str, Path], pom: PomXML):
        self.root_pom_path: Path = Path(pom_path)
        """Path to the root pom.xml file."""

        self.root_pom = pom
        """PomXML object for the root pom.xml file."""

        self.initialized = False
        """Whether the Cobertura Maven plugin has been initialized in the root pom.xml."""

    @staticmethod
    def load(pom_path: Union[str, Path]):
        """Load the Cobertura Maven plugin controller from the project pom.xml."""
        pom = PomXML.from_file(pom_path)
        return CoberturaMavenPlugin(pom_path, pom)

    def initialize(self):
        """
        Initialize Cobertura Maven plugin in the pom.xml.
        Note that this is a destructive operation, and will overwrite the pom.xml file.
        """
        self.root_pom.add_maven_plugin(
            plugin_type="reporting",
            **COBERTURA_DETAILS
        )
        self.root_pom.save_to_disk()

        self.initialized = True

    def get_report(self, module: Path):
        """
        Get the Cobertura report for the given module.
        """
        expected_file = module / 'target' / 'site' / 'cobertura' / 'coverage.xml'

        # Certain projects may not have a coverage.xml file, so we need to check for its existence
        # Hypothesized to be projects that are just parents of other projects
        if expected_file.exists():
            return parse_xml_as_dict(expected_file)
        else:
            return None

    def get_all_reports(self):
        """
        Aggregate the Cobertura reports of all submodules in the current repository.
        """
        all_coverage = {}
        root_path, submodules = self.root_pom.find_all_submodules()
        root = Path(root_path)

        for module in submodules:
            report = self.get_report(root / module)
            if report is not None:
                all_coverage[module] = report

        return all_coverage
