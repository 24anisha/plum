import pytest
from plum.actions.java_mvn_actions import JavaMavenActions
from plum.environments.java_repo import JavaRepository


@pytest.mark.skip(reason="Need test repositories")
def test_spotbugs_execution():
    """Test spotbugs execution and check if SARIf is produced."""
    # TODO try running the test with the username/repo name as input (make it clone)
    # fix any bugs that come up
    # TODO then, see what changes need to be made to the java side so that you can use a repo that is local, not cloned
    repo = JavaRepository("/home/anisagarwal/data/plum_trials", "sauce-code/cuckoo")
    repo.setup()

    docker_image = "maven"
    docker_tag = "3.3-jdk-8"
    # plum = JavaMavenActions(repo, docker_image, docker_tag, local_repository)
    plum = JavaMavenActions(repo, docker_image, docker_tag, "/home/anisagarwal/data/java_plum")

    build_result = plum.build()
    # print("########################## BUILD RESULT: ", build_result)
    # assert build_result["status_result"] == ""

    compile_result = plum.compile()
    # print("########################## COMPILE RESULT: ", compile_result)

    # assert compile_result["status_result"] == "success"

    errors = plum.spotbugs("/home/anisagarwal/data", spotbugs_path="/home/anisagarwal/data/java_plum/spotbugs")
    # errors = plum.spotbugs("/home/anisagarwal/data/plum_trials/sauce-code--cuckoo")
    assert len(errors) > 0


if __name__ == "__main__":
    test_spotbugs_execution()
