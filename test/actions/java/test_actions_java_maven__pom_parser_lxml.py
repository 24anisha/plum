import pytest
from pathlib import Path
from plum.actions.java.maven._pom_parser_lxml import PomXML

@pytest.fixture(scope="module")
def sample_pom_xml():
    """Fixture to read a pom.xml file from the test directory."""
    test_dir = Path(__file__).parent  # Adjust if your test structure is different
    sample_pom_path = test_dir / '_example_pom.xml'
    return PomXML.from_file(sample_pom_path)

def test_get_modules(sample_pom_xml):
    """Test the get_modules function from the PomXML class."""
    expected_modules = [
        'apollo-buildtools',
        'apollo-common',
        'apollo-biz',
        'apollo-configservice',
        'apollo-adminservice',
        'apollo-portal',
        'apollo-assembly',
        'apollo-audit',
    ]

    # Retrieve modules using the function under test
    modules = sample_pom_xml.get_modules()

    # Assert that the retrieved modules match the expected list
    assert modules == expected_modules, "The modules retrieved from get_modules() do not match the expected list"
