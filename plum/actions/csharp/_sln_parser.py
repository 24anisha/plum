from pathlib import Path
from lxml import etree as ET
import re
from typing import List, NamedTuple, Optional, Union

class CsProj:
    """
    Represents a C# project (.csproj) file, providing methods to interact with and extract information from it.
    """

    class PackageReference(NamedTuple):
        """
        Represents a package reference from the .csproj file.

        Attributes:
            name (str): The name of the package.
            version (str): The version of the package.
        """
        name: str
        """The name of the package."""
        version: Optional[str]
        """The version of the package."""

    def __init__(
            self,
            csproj_path: str,
            xml_tree: ET.ElementTree,
            name: Optional[str]=None,
            relative_path: Optional[str]=None,
            project_id: Optional[str]=None
        ):
        """
        Note that the ideal way to create a CsProj object is via the `from_file` method.
        If directly instantiating this class, the path

        Args:
            csproj_path: The file path to the .csproj file.
            xml_tree: The XML tree of the .csproj file.
            name: The name of the project.
            relative_path: The relative path to the project, with backslashes replaced by forward slashes.
            project_id: The unique identifier for the project.
        """
        self.csproj_path = csproj_path
        """File path to the .csproj file."""
        self.tree = xml_tree
        """XML tree of the .csproj file."""
        self.name = name
        """Name of project."""
        self.path = relative_path and relative_path.replace('\\', '/')
        """Relative path from solution to project."""
        self.project_id = project_id
        """Project GUID."""

        self.target_frameworks = self.get_target_framework()
        """Target framework(s) for the project."""
        self._package_references = None
        """Cache for package references."""

    @staticmethod
    def from_file(
            csproj_path: str,
            name: Optional[str]=None,
            path: Optional[str]=None,
            project_id: Optional[str]=None
        ):
        """Create a CsProj instance directly from a .csproj file."""
        with open(csproj_path, 'r') as file:
            tree = ET.parse(file)

        return CsProj(csproj_path, tree, name, path, project_id)

    def get_package_references(self) -> List[PackageReference]:
        """Retrieve all package references in this project."""
        if self._package_references:
            return self._package_references

        path = '//PackageReference'
        package_references = []
        for elem in self.tree.xpath(path):
            package_name = elem.attrib.get('Include')
            package_version = elem.attrib.get('Version')
            if package_name:
                package_references.append(CsProj.PackageReference(package_name, package_version))
        return package_references

    def get_target_framework(self) -> List[str]:
        """Retrieve the target framework(s) for this project."""
        frameworks = []

        # Check for both single TargetFramework and multiple TargetFrameworks
        single_framework = self.tree.find('.//TargetFramework')
        if single_framework is not None and single_framework.text:
            frameworks.append(single_framework.text)

        multiple_frameworks = self.tree.find('.//TargetFrameworks')
        if multiple_frameworks is not None and multiple_frameworks.text:
            frameworks.extend(multiple_frameworks.text.split(';'))

        return frameworks

    def get_test_project_type(self):
        """Return the test project type of this project."""
        package_references = self.get_package_references()

        # NUnit and xunit need to come first
        known_test_packages = [
            'NUnit',
            'xunit',
            'xunit.runner.visualstudio'
            'Microsoft.NET.Test.Sdk',
        ]

        for package in package_references:
            if package.name in known_test_packages:
                return package.name

        return None

    def is_test_project(self):
        """Return True if this project is a test project."""
        return self.get_test_project_type() is not None

    def __repr__(self):
        return f"CsProj(name={self.name}, path={self.path}, project_id={self.project_id})"

    def to_dict(self):
        return {
            'name': self.name,
            'path': self.path,
            'project_id': self.project_id,
            'target_frameworks': self.target_frameworks,
            'csproj_path': str(self.csproj_path),
            'package_references': [
                {'name': ref.name, 'version': ref.version}
                for ref in self.get_package_references()
            ],
            'is_test_project': self.is_test_project()
        }

class Project:
    """
    Represents a general project within a solution, holding basic information about the project.
    In C# solutions, certain directories are also considered projects.
    """
    def __init__(self, name, relative_path, project_id):
        """
        Args:
            name: Name of project.
            path: Relative path from solution to project.
            project_id: Project GUID.
        """
        self.name = name
        """Name of project."""
        self.path = relative_path.replace('\\', '/')
        """Relative path from solution to project."""
        self.project_id = project_id
        """Project GUID."""

    def create_csproj(self, base_path: Union[str, Path]):
        """Create a CsProj object from this project

        Args:
            base_path (str): The base path to the solution file.

        Returns:
            CsProj: A CsProj object. None if this project is not a .csproj file.
        """
        # Check this Project is a real .csproj file
        if not self.path.endswith('.csproj'):
            return None

        csproj_path = Path(base_path) / self.path
        return CsProj.from_file(csproj_path, self.name, self.path, self.project_id)

    def __repr__(self):
        return f"Project(name={self.name}, path={self.path}, project_id={self.project_id})"

    def to_dict(self):
        return {
            'name': self.name,
            'path': self.path,
            'project_id': self.project_id
        }

class Solution():
    """
    Represents a Visual Studio solution file, allowing extraction and manipulation of its contained projects.
    """

    PROJECT_REGEX = re.compile(r'Project\("\{.*\}"\) = "(.*)", "(.*)", "\{(.*)\}"')
    """Regex to match a project in a solution file."""

    def __init__(
            self,
            base_path: Union[str, Path],
            solution_filename: str,
            solution_contents: List[str]
        ):
        self.base_path = Path(base_path)
        """The base path to the solution file."""
        self.solution_filename = solution_filename
        """The name of the solution file."""

        self.solution_contents = solution_contents
        self.projects = []
        """Lazily loaded list of projects."""

    @staticmethod
    def from_file(solution_path):
        with open(solution_path, 'r') as file:
            solution_data = file.readlines()

        base_path = Path(solution_path).parent
        solution_file_name = Path(solution_path).name
        return Solution(base_path, solution_file_name, solution_data)

    def get_projects(self) -> List[Project]:
        """
        Retrieve all projects from this solution.
        In C# solutions, certain directories are also considered projects.

        Returns:
            List[Project]: A list of Project objects.
        """
        if not self.projects:
            for line in self.solution_contents:
                match = Solution.PROJECT_REGEX.match(line.strip())
                if match:
                    project_name, project_path, project_id = match.groups()
                    self.projects.append(Project(project_name, project_path, project_id))
        return self.projects

    def get_test_projects(self) -> List[CsProj]:
        """
        Retrieve only all test projects from this solution.

        Returns:
            List[CsProj]: A list of CsProj objects.
        """
        test_projects = []
        for project in self.get_projects():
            csproj = project.create_csproj(self.base_path)
            if csproj is not None and csproj.is_test_project():
                test_projects.append(csproj)
        return test_projects

    def __repr__(self):
        return f"Solution('{self.solution_file_name}', base_path='{self.base_path}', projects={len(self.projects)})"

    def to_dict(self):
        # First split the solution into projects and csprojects
        projects = self.get_projects()
        pure_projects = []
        csprojects = []
        for project in projects:
            csproj = project.create_csproj(self.base_path)
            if csproj:
                csprojects.append(csproj)
            else:
                pure_projects.append(project)

        projects_dict = [project.to_dict() for project in pure_projects]
        csprojects_dict = [csproj.to_dict() for csproj in csprojects]

        return {
            'solution_filename': self.solution_filename,
            'base_path': str(self.base_path),
            'projects': projects_dict,
            'csprojects': csprojects_dict
        }
