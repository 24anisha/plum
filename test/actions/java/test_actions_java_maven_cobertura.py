import pytest
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET


from plum.actions.java.maven.cobertura import COBERTURA_DETAILS, CoberturaMavenPlugin


NS = "{http://maven.apache.org/POM/4.0.0}"


@pytest.fixture(scope="session")
def prepared_pom(tmp_path_factory):
    # Create a session-scoped temporary directory
    tmp_path = tmp_path_factory.mktemp("data")

    # Copy over the pom.xml file from the test directory
    test_dir = Path(__file__).parent
    original_pom_path = test_dir / "_example_pom.xml"
    temp_pom_path = tmp_path / "pom.xml"
    shutil.copyfile(original_pom_path, temp_pom_path)

    # Initialize cobertura on the temporary pom file
    CoberturaMavenPlugin.load(temp_pom_path).initialize()
    return temp_pom_path

def _get_cobertura_plugin(prepared_pom):
    tree = ET.parse(prepared_pom)
    root = tree.getroot()

    # Find all reporting plugins
    plugins = root.find(f"{NS}reporting").find(f"{NS}plugins").findall(f"{NS}plugin")

    # There should only be one cobertura plugin, so just use next() to get the first plugin with the right IDs
    cobertura_plugin = next(
        (
            plugin for plugin in plugins
            if plugin.find(f'{NS}groupId').text == COBERTURA_DETAILS['group_id'] and
            plugin.find(f'{NS}artifactId').text == COBERTURA_DETAILS['artifact_id']
        ),
        None
    )

    return cobertura_plugin

def test_no_duplicate_sections__reporting(prepared_pom):
    tree = ET.parse(prepared_pom)
    root = tree.getroot()

    reporting = root.findall(f"{NS}reporting")
    assert len(reporting) == 1, "More than one reporting section was found."

def test_no_duplicate_sections__plugins(prepared_pom):
    tree = ET.parse(prepared_pom)
    root = tree.getroot()

    plugins_section = root.find(f"{NS}reporting").findall(f"{NS}plugins")
    assert len(plugins_section) == 1, "More than one plugins section was found."

def test_no_duplicate_cobertura_plugin(prepared_pom):
    tree = ET.parse(prepared_pom)
    root = tree.getroot()

    plugins = root.find(f"{NS}reporting").find(f"{NS}plugins").findall(f"{NS}plugin")

    seen = set()
    for plugin in plugins:
        identifier = (plugin.find(f'{NS}groupId').text, plugin.find(f'{NS}artifactId').text)
        assert identifier not in seen, f"Duplicate plugin found: {identifier}"
        seen.add(identifier)

def test_cobertura_plugin_added(prepared_pom):
    cobertura_plugin = _get_cobertura_plugin(prepared_pom)

    assert cobertura_plugin is not None, "Cobertura plugin was not added."

def test_cobertura_plugin_properties(prepared_pom):
    cobertura_plugin = _get_cobertura_plugin(prepared_pom)

    assert cobertura_plugin.find(f'{NS}version').text == COBERTURA_DETAILS['version'], "Cobertura version is incorrect."
