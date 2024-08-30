"""
Utilities for parsing and interpreting Cobertura coverage reports.

Although Cobertura is primarily used for Java,
its XML report format is adopted by various code coverage tools across different programming languages,
including Python and JavaScript.
"""


from pathlib import Path
from typing import Union
import xmltodict


def parse_xml_as_dict(path: Union[str, Path]) -> dict:
    """
    Parse the Cobertura coverage report as a JSON file.
    :param path: path to the Cobertura coverage report
    :returns: the parsed JSON data
    """
    xml_data = Path(path).read_text()

    # Parse XML data into a dictionary using xmltodict
    coverage_report = xmltodict.parse(xml_data)

    return coverage_report

def get_function_coverage(cobertura_report: dict, hash2function: dict, language: str) -> dict[str, list[int]]:
    """
    Generate a per-function coverage, where the keys of the dictionary are the function hashes and
    the values are integer lists of covered lines.
    """
    restructured_report = _restructure_coverage_report(cobertura_report, language)

    fn2coverage = {}
    for fnhash, function in hash2function.items():
        # if the focal file is in the coverage report, check if the focal function has covered lines

        if function.relative_path in restructured_report.keys():
            file_executed_lines = restructured_report[function.relative_path]
            covered_lines = [element for element in file_executed_lines if function.start_line + 1 <= element <= function.end_line + 1]
            # if covered_lines is only 1, then only the signature is being run, not the test itself
            if len(covered_lines) == 1 and function.end_line - function.start_line == 0:
                continue
            elif len(covered_lines) > 0:
                fn2coverage[fnhash] = covered_lines

    return fn2coverage

def _restructure_coverage_report(cobertura_report: dict, language: str) -> dict[str, list[int]]:
    """
    Parses and restructures the coverage report for easier matching
    from covered lines to covered functions.
    :param cobertura_report: the .json version of the .xml
                            cobertura coverage report to restructure
    :returns: dict report: the restructured coverage report that maps
                            the relative path of a file to a list of its covered lines
    """
    restructured_report = {}

    if language == "csharp":
        packages = cobertura_report['coverage_data']['.']['coverage']['packages']['package']
    else:
        packages = cobertura_report['coverage']['packages']['package']    
    
    # Each package is represented by a dict.
    # If there are multiple packages in the repo, packages will be a list.
    # If there is only one package, packages will be the dict of the sole package.

    # Get list containing file-level coverage information for each file in the package
    if isinstance(packages, dict):
        file_dicts = packages['classes']['class']

    else:
        file_dicts = []
        for package in packages:
            if isinstance(package['classes']['class'], dict):
                file_dicts.append(package['classes']['class'])
            elif isinstance(package['classes']['class'], list):
                file_dicts.extend(package['classes']['class'])

    # Make sure file_dicts is a list of dicts (even if there is only one file in the list)
    if isinstance(file_dicts, dict):
        file_dicts = [file_dicts]

    for file_dict in file_dicts:
        filepath = file_dict['@filename']
        executed_lines = []
        restructured_report[filepath] = executed_lines

        # No line coverage in the file at all
        if file_dict['lines'] == None:
            continue

        # Check whether file has only one line
        if isinstance (file_dict['lines']['line'], dict):
            lines = [file_dict['lines']['line']]
        else:
            lines = file_dict['lines']['line']

        # Iterate through the lines of the file and append the line numbers
        # of lines that are "hit" (covered) by the test suite
        for line in lines:
            if line['@hits'] != '0':
                executed_lines.append(int(line['@number']))

    return restructured_report
