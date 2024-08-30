import io
import os
import re
import logging
import subprocess
import requests
import zipfile
from pathlib import Path
import shlex


from plum.utils.cobertura import get_function_coverage
from plum.actions.actions import Actions
from plum.actions.java.maven.cobertura import CoberturaMavenPlugin
from plum.utils.logger import Logger

TIMEOUT = 1000
DOCKER_TIMEOUT = 900


class JavaMavenActions(Actions):
    """
    Class used to represent the Maven actions that can be taken on an environment object
    in Java

    Attributes:
    -----------
    environment: the environment object that we are taking actions on
                Could be a repository, a directory, etc etc.

    """

    def __init__(
        self,
        environment,
        docker_image,
        docker_tag,
        docker_work_dir="/usr/src/mymaven",
        local_repository="",
    ):
        super().__init__(environment)
        self.docker_image = docker_image
        self.docker_tag = docker_tag
        self.docker_work_dir = docker_work_dir
        self.repo_full_path = Path(os.path.join(
                environment.base, environment.internal_repo_path
        )).resolve()
        if environment.repo_type.name == 'LOCAL' or environment.repo_type.name == 'TEST':
            self.repo_full_path = environment.base

        self.spotbugs_path = ""
        self.repository_setting = ""
        if local_repository:
            self.repository_setting = f"-v {local_repository}:/root/.m2"

        self.cobertura_plugin: CoberturaMavenPlugin = None
        """Cobertura Maven plugin helper class. Initialized on demand."""

        self.maven_logging_level = "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn"

    def clean(self):
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.docker_image}:{self.docker_tag} mvn clean -B {self.maven_logging_level}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            status_result = self.parse_mvn_status(stdout)
            result = {"status_result": status_result, "stdout": stdout, "stderr": stderr}

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result

    def compile(self):
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.repository_setting} {self.docker_image}:{self.docker_tag} mvn clean compile -B {self.maven_logging_level}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            status_result = self.parse_mvn_status(stdout)
            result = {"status_result": status_result, "stdout": stdout, "stderr": stderr}

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result

    def build(self):
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.repository_setting} {self.docker_image}:{self.docker_tag} mvn clean install -B {self.maven_logging_level}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )

            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            status_result = self.parse_mvn_status(stdout)
            test_results = self.parse_mvn_test(stdout)
            result = {
                "status_result": status_result,
                "test_results": test_results,
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result

    def run_test_suite(self, timeout=TIMEOUT):
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.repository_setting} {self.docker_image}:{self.docker_tag} mvn test -B {self.maven_logging_level}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=timeout
            )

            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            status_result = self.parse_mvn_status(stdout)
            test_results = self.parse_mvn_test(stdout)
            result = {
                "status_result": status_result,
                "test_results": test_results,
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired:
            Logger().get_logger().error(f"TimeoutExpired: Your timeout is currently {timeout}s. Increase timeout if needed")
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result


    def write_gentest_file(self, generated_test, package_import, class_name):
        """
        Helper function called by run_generated test.
        Format the generated test correctly to be written to a file and run
        Check whether the package, imports and class structure exists in the
        generated test. Replace the package if so
        """

        gentest_lines = generated_test.split('\n')  # Split the text into lines
        testfile_code = []
        ignore_lines = [
            "import org.junit.Test;",
            "import static org.junit.Assert.*;",
            ""
        ]
        # ignore the lines we want to write manually
        for i, line in enumerate(gentest_lines):
            if (line.strip().startswith("package") and i == 0) or line in ignore_lines:
                continue
            testfile_code.append(line)

        cleaned_gentest = '\n'.join(testfile_code)  # Join the remaining lines back into a single string

        # if the model wrote a class, add the entire class. otherwise, write a class and add the test
        if "public class" in cleaned_gentest:
            cleaned_gentest = f"""
package {package_import};

import org.junit.Test;
import static org.junit.Assert.*;

{cleaned_gentest}
"""
        else:
            cleaned_gentest = f"""
package {package_import};

import org.junit.Test;
import static org.junit.Assert.*;

public class {class_name} {{
    {cleaned_gentest}
}}
"""
        return cleaned_gentest


    def run_generated_test(self, generated_test):
        """
        Given test code, insert the code at the correct location in the Java repo
        and run the generated test, returning the result, if possible to do so with the repo.

        :param generated_test: code to insert into the newly created test file & run
        :param class_name: the name of the test class generated by the model. If 
                            no class was generated, class name will default to GeneratedTest
        returns: 
            result = {
                "status_result": status_result,
                "test_results": test_results,
                "stdout": stdout,
                "stderr": stderr,
            }
        """
        # set the path to which we will write the generated test
        # If we haven't run get_gentest_directory already, run it now to get the location
        test_write_path = self.environment.test_write_location
        if not test_write_path:
            test_write_path = self.environment.get_gentest_directory()
        
        if test_write_path == "not_possible":
            result = {"success": False, "stdout": "n/a", "stderr": f"Cannot parse structure of the repo to write and run generated tests"}
            return result

        class_name = self.get_class_name(generated_test)

        # given a path such as src/test/java/foo/bar/alpha, returns foo.bar.alpha, 
        # which needs to be added at the beginning of the test file
        package_import = str(test_write_path).split("src/test/java/")[1].replace("/", ".")
        # write a file whose first line is the package information (all the directories after java to get to this file)

        testfile_code = self.write_gentest_file(generated_test, package_import, class_name)
        testfile_path = test_write_path / f"{class_name}.java"

        # if the file already exists, save the existing code and re-write it after running our test class
        contents = None
        if os.path.exists(testfile_path):
            contents = open(testfile_path).read()

        with open(testfile_path, "w") as tf:
            Logger().get_logger().info(f"### Generated Test to be Run: ###\n```{testfile_code}\n```")
            tf.write(testfile_code)
        
        test_result = self.run_test_class(f"{package_import}.{class_name}")

        #   rewrite original file contents if we replaced the existing code
        if contents:
            with open(testfile_path, "w") as f:
                f.write(contents)
        
        if not contents:
            os.remove(testfile_path)

        return test_result


    def get_class_name(self, class_code):
        """
        Get the class name from the generated test. If the code
        has no class, set the class name to GeneratedTest
        """
        # Search for the pattern "public class [ClassName]"
        class_name_match = re.search(r"public class (\S+)", class_code)
        if class_name_match:
            class_name = class_name_match.group(1)
        else:
            class_name = "GeneratedTest"
        return class_name


    def run_test_class(self, class_name):
        """
        Run a single specified test class.
        """
        try:
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.repository_setting} {self.docker_image}:{self.docker_tag} mvn -Dtest={class_name} -B test {self.maven_logging_level}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            status_result = self.parse_mvn_status(stdout)
            test_results = self.parse_mvn_test(stdout)
            result = {
                "status_result": status_result,
                "test_results": test_results,
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result

    def run_test_case(self, class_name, test_method_name):
        try:
            full_test_name = f"{class_name}#{test_method_name}"
            command = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.repository_setting} {self.docker_image}:{self.docker_tag} mvn -Dtest={full_test_name} -B test {self.maven_logging_level}"
            output = subprocess.run(
                shlex.split(command), capture_output=True, timeout=TIMEOUT
            )
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            status_result = self.parse_mvn_status(stdout)
            test_results = self.parse_mvn_test(stdout)
            result = {
                "status_result": status_result,
                "test_results": test_results,
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result

    def install_spotbugs(self, spotbugs_path):
        """Download Spotbugs from official release page to home directory"""
        r = requests.get(
            "https://github.com/spotbugs/spotbugs/releases/download/4.7.3/spotbugs-4.7.3.zip"
        )
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(spotbugs_path)

    def spotbugs(self, spotbugs_path="/home/spotbugs"):
        """Run Spotbugs on the project by using the Spotbugs 4.7.3 JAR file"""
        try:

            spotbugs_path = Path(spotbugs_path)
            self.spotbugs_path = str(spotbugs_path)
            if not spotbugs_path.exists():
                self.install_spotbugs(spotbugs_path)
                Logger().get_logger().info("Installing spotbugs")

            spotbugs_output_path = Path(spotbugs_path / "tempfiles")
            spotbugs_output_path.mkdir(parents=True, exist_ok=True)

            repo = self.environment.internal_repo_path
            # commandS = f"docker run --rm -v {local_workspace}:/home -w /home {self.docker_image}:{self.docker_tag} java -jar /home/spotbugs/spotbugs-4.7.3/lib/spotbugs.jar -textui -sarif=/home/{repo}/spotbugs.sarif -low /home/{repo}"
            # commandS = f"docker run --rm -v {local_workspace}:/home -w /home {self.docker_image}:{self.docker_tag} java -jar /home/spotbugs/spotbugs-4.7.3/lib/spotbugs.jar -textui -sarif={self.docker_work_dir}/spotbugs.sarif -low {self.docker_work_dir}"
            commandS = f"docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -v {str(spotbugs_path)}:/home/spotbugs/ {self.docker_image}:{self.docker_tag} java -jar /home/spotbugs/spotbugs-4.7.3/lib/spotbugs.jar -textui -sarif={self.docker_work_dir}/spotbugs.sarif -low {self.docker_work_dir} {self.maven_logging_level}"

            output = subprocess.run(
                shlex.split(commandS), capture_output=True, timeout=TIMEOUT
            )
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            result = {"stdout": stdout, "stderr": stderr.strip(), "spotbugs_sarif": Path(self.repo_full_path) / "spotbugs.sarif"}

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result

    def run_custom_command(self, command):
        try:
            command = f'docker run --rm -v {self.repo_full_path}:{self.docker_work_dir} -w {self.docker_work_dir} {self.repository_setting} {self.docker_image}:{self.docker_tag} {command}'
            output = subprocess.run(shlex.split(command), capture_output=True, timeout=TIMEOUT)
            stdout = output.stdout.decode("utf-8")
            stderr = output.stderr.decode("utf-8")
            status_result = self.parse_mvn_status(stdout)
            result = {"status_result": status_result, "stdout": stdout, "stderr": stderr}

        except subprocess.TimeoutExpired:
            result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}

        return result

    def get_coverage(self):
        """
        Run Cobertura Maven plugin to generate coverage report.
        Note that the current methodology is hard coupled with Maven.
        """
        pom_path = Path(self.repo_full_path) / "pom.xml"
        if not self.cobertura_plugin:
            self.cobertura_plugin = CoberturaMavenPlugin.load(pom_path)

        # Note that this is NOT honored in a monorepo.
        output_dir = Path(self.repo_full_path) / "target/site/cobertura"
        custom_command = (
            "mvn cobertura:cobertura "
            "-Dcobertura.aggregate=true " # Aggregate coverage report across modules.
            "-Dcobertura.report.format=xml " # Report in XML instead of HTML.
            f"-Dcobertura.outputDirectory={output_dir} " # Specify output directory.
            f" {self.maven_logging_level} "
        )

        try:
            self.cobertura_plugin.initialize()
        except Exception as e:
            return {
                "success": False,
                "stdout": f"Exception while trying to initialize Cobertura on {pom_path}",
                "stderr": e
            }

        result = self.run_custom_command(custom_command)

        # # Failed to generate coverage report
        if result["status_result"] != "SUCCESS":
            return result

        # Read the coverage report
        coverage_reports = self.cobertura_plugin.get_all_reports()

        return coverage_reports

    def get_covered_functions(self, cobertura_coverage_report: dict = None):
        """
        Get list of focal functions with coverage
        :cobertura_coverage_report: the coverage report in cobertura format. Will execute coverage if not provided.

        :returns: dictionary mapping function hash to list of covered lines
        """
        if cobertura_coverage_report is None:
            Logger().get_logger().info("getting coverage report...")
            try:
                cobertura_coverage_report = self.get_coverage()
            except subprocess.TimeoutExpired:
                result = {"success": False, "stdout": "n/a", "stderr": f"Timeout"}
                return result

            # if it did not succeed in getting the coverage report, return the unsuccessful coverage dictionary
            if cobertura_coverage_report.get("success", "") == False:
                return cobertura_coverage_report

        cobertura_coverage_report = self._adapt_cobertura_report(cobertura_coverage_report)

        # Ensure that the Java environment we're using has hash2function populated.
        if not hasattr(self.environment, 'hash2function'):
            _ = self.environment.get_functions()

        fn2coverage = get_function_coverage(cobertura_coverage_report, self.environment.hash2function, "java")

        return fn2coverage

    # TODO: C# has this same method. Refactor to a common method.
    def _adapt_cobertura_report(self, report: dict):
        """
        Adapt the cobertura report to the format that the coverage report expects.

        Mainly carries out two operations.
        1. Renames the sources
            The sources point to the docker mount path, which is not the repo full path.
            ex) old: /usr/src/mymaven/apollo-adminservice/src/main/java
            ex) new: /datadisk/src/apollo/apollo-adminservice/src/main/java
        2. Renames the package file paths
            The file paths are relative to "com" or "org" or "net" etc. Change them to be relative to the repo root.
            ex) old: com/ctrip/framework/apollo/adminservice/config/ConfigServiceConfig.java
            ex) new: apollo-adminservice/src/main/java/com/ctrip/framework/apollo/adminservice/config/ConfigServiceConfig.java
        """
        # Check for multiproject repos
        if '.' in report:
            if len(report) > 1:
                logging.warning(f"Found multiple projects in the coverage report. Using aggregated report.")
            report = report['.']

        # Change the Cobertura source paths to point to the repo full path instead of the docker mount path.
        new_sources = []
        for source in report['coverage']['sources']['source']:
            # The source states docker work dir, replace it with the repo full dir.
            if source.startswith(self.docker_work_dir):
                source = source.replace(self.docker_work_dir, str(self.repo_full_path))
            new_sources.append(source)
        report['coverage']['sources']['source'] = new_sources

        # Change the Cobertura packages to point to the repo full path instead of the docker mount path.
        packages = report['coverage']['packages']['package']
        if isinstance(packages, dict):
            packages = [packages]

        for package in packages:
            file_dicts = package['classes']['class']
            if isinstance(file_dicts, dict):
                file_dicts = [file_dicts]

            for f in file_dicts:
                filepath = f.get('@filename')

                for source in new_sources:
                    potential_path = Path(source) / filepath
                    if potential_path.exists():
                        f['@filename'] = str(potential_path.relative_to(self.repo_full_path))
                        break

        return report

    # ------------------- PARSING UTILITIES -------------------

    def parse_spotbugs(self, maven_output):
        # Find all matches for BugInstance, Error, and Total bugs information in the Maven output
        bug_instance_match = re.search(r"BugInstance size is (\d+)", maven_output)
        error_size_match = re.search(r"Error size is (\d+)", maven_output)
        total_bugs_match = re.search(r"Total bugs: (\d+)", maven_output)

        # Extract the numbers from the matches, or default to 0 if not found
        bug_instance_count = (
            int(bug_instance_match.group(1)) if bug_instance_match else 0
        )
        error_size_count = int(error_size_match.group(1)) if error_size_match else 0
        total_bugs_count = int(total_bugs_match.group(1)) if total_bugs_match else 0

        # Assemble the results dictionary
        spotbugs_result = {
            "bug_instance_count": bug_instance_count,
            "error_size_count": error_size_count,
            "total_bugs_count": total_bugs_count,
        }

        return spotbugs_result

    def parse_mvn_test(self, maven_output):
        # Find all matches of the "Results" section in the Maven output
        results_matches = re.findall(
            r"\[INFO\] Results:\s*\[INFO\]\s*\n\[INFO\]\s*Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)",
            maven_output,
        )

        # Summing up the values for each category from the "Results" section
        tests_run = sum(int(match[0]) for match in results_matches)
        failures = sum(int(match[1]) for match in results_matches)
        errors = sum(int(match[2]) for match in results_matches)
        skipped = sum(int(match[3]) for match in results_matches)

        result_status = self.parse_mvn_status(maven_output)

        test_results = {
            "tests_run": tests_run,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
        }

        return test_results

    def parse_mvn_status(self, maven_output):
        # Determining overall success or failure based on BUILD status
        overall_status_match = re.search(r"BUILD (SUCCESS|FAILURE)", maven_output)
        # Enable printing the output only for debugging this library
        # Logger().get_logger().info(f"MAVEN OUTPUT: {maven_output}")
        Logger().get_logger().info(f"OVERALL STATUS MATCH: {overall_status_match}")
        overall_status = (
            overall_status_match.group(1) if overall_status_match else "UNKNOWN"
        )

        return overall_status
