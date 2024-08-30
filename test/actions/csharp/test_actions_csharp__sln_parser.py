import pytest


from plum.actions.csharp._sln_parser import Project, Solution


@pytest.fixture()
def temp_solution_file(tmp_path):
    content = """
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31903.59
MinimumVisualStudioVersion = 10.0.40219.1
Project("{2150E333-8FDC-42A3-9474-1A3956D46DE8}") = "src", "src", "{6267E2ED-942C-497D-BFC9-B3CE0AFC276F}"
EndProject
Project("{2150E333-8FDC-42A3-9474-1A3956D46DE8}") = "test", "test", "{962C5ACA-AB2B-4E9B-9EBB-7E7EE28CDBB1}"
EndProject
Project("{9A19103F-16F7-4668-BE54-9A1E7A4F7556}") = "MediatR", "src\\MediatR\\MediatR.csproj", "{12DA3F16-060B-467A-993F-2DF25EE6E6A8}"
EndProject
Project("{9A19103F-16F7-4668-BE54-9A1E7A4F7556}") = "MediatR.Tests", "test\\MediatR.Tests\\MediatR.Tests.csproj", "{4FB0CFC4-90E3-467F-9704-6FBF637F9B4B}"
EndProject
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{12DA3F16-060B-467A-993F-2DF25EE6E6A8}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{12DA3F16-060B-467A-993F-2DF25EE6E6A8}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{12DA3F16-060B-467A-993F-2DF25EE6E6A8}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{12DA3F16-060B-467A-993F-2DF25EE6E6A8}.Release|Any CPU.Build.0 = Release|Any CPU
		{4FB0CFC4-90E3-467F-9704-6FBF637F9B4B}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{4FB0CFC4-90E3-467F-9704-6FBF637F9B4B}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{4FB0CFC4-90E3-467F-9704-6FBF637F9B4B}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{4FB0CFC4-90E3-467F-9704-6FBF637F9B4B}.Release|Any CPU.Build.0 = Release|Any CPU
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
	GlobalSection(NestedProjects) = preSolution
		{12DA3F16-060B-467A-993F-2DF25EE6E6A8} = {6267E2ED-942C-497D-BFC9-B3CE0AFC276F}
		{4FB0CFC4-90E3-467F-9704-6FBF637F9B4B} = {962C5ACA-AB2B-4E9B-9EBB-7E7EE28CDBB1}
	EndGlobalSection
	GlobalSection(ExtensibilityGlobals) = postSolution
		SolutionGuid = {D58286E3-878B-4ACB-8E76-F61E708D4339}
	EndGlobalSection
EndGlobal
"""
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "mock_solution.sln"
    p.write_text(content)
    return str(p)  # returning the file path as a string

def _assert_project(project: Project, expected_guid: str, expected_name: str, expected_path: str):
    assert project.project_id == expected_guid, "Expected guid to be {}".format(expected_guid)
    assert project.name == expected_name, "Expected name to be {}".format(expected_name)
    assert project.path == expected_path, "Expected path to be {}".format(expected_path)

def test_solution_parser_parses_projects(temp_solution_file):
    sln = Solution.from_file(temp_solution_file)
    projects = sln.get_projects()
    assert len(projects) == 4, "Expected 4 C# projects from the mock data"

def test_solution_parser_project_properties(temp_solution_file):
    sln = Solution.from_file(temp_solution_file)
    projects = sln.get_projects()

    _assert_project(projects[0], "6267E2ED-942C-497D-BFC9-B3CE0AFC276F", "src", "src")
    _assert_project(projects[1], "962C5ACA-AB2B-4E9B-9EBB-7E7EE28CDBB1", "test", "test")
    _assert_project(projects[2], "12DA3F16-060B-467A-993F-2DF25EE6E6A8", "MediatR", "src/MediatR/MediatR.csproj")
    _assert_project(projects[3], "4FB0CFC4-90E3-467F-9704-6FBF637F9B4B", "MediatR.Tests", "test/MediatR.Tests/MediatR.Tests.csproj")


def test_solution_parser_no_projects(tmp_path):
    # Test the parser with an empty solution file (no projects)
    empty_solution_content = "Microsoft Visual Studio Solution File, Format Version 12.00"
    empty_solution_file = tmp_path / "empty_mock_solution.sln"
    empty_solution_file.write_text(empty_solution_content)

    parser = Solution.from_file(str(empty_solution_file))
    assert len(parser.get_projects()) == 0, "Expecting 0 projects from empty solution"
