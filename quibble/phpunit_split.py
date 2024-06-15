#!/usr/bin/env python3
"""Library for processing the output of phpunit's `--list-tests-xml`
and creating a modified `phpunit.xml` that contains the same tests
as the provided testsuite, but split out into a number of smaller
chunks.

The script is executable and can be run standalone for debugging
purposes - developers may want to be able to generate the same split
chunks that Quibble would generate without having to run the whole
of Quibble.
"""
import logging
import os
import json
import sys
import re
from xml.etree import ElementTree as ET
from xml.dom.minidom import parseString

logger = logging.getLogger(__name__)


class ResultCacheParser:
    """Load the contents of a phpunit result cache file
    (.phpunit.result.cache) into memory as a dictionary, summing
    the amount of time spent for tests in each class."""

    def parse_result_cache(self, cache_file):
        """Parse a `.phpunit.result.cache` file
        - cache_file - the name of the file (string)
        """
        with open(cache_file, 'r') as file:
            cache_data = file.read()
        cache_array = json.loads(cache_data)
        times = cache_array['times']
        time_spent_per_class = {}
        for test_case, time_spent in times.items():
            class_name = test_case.split('::')[0]
            time_spent_per_class[class_name] = (
                time_spent_per_class.get(class_name, 0) + time_spent
            )
        return time_spent_per_class


class TestListParser:
    """Process the XML file created by phpunit's --list-tests-xml and
    return a list of test classes annotated with timing data if
    available."""

    def extract_namespace(self, test_case_class):
        """Split a namespace-qualified PHP class name and return
        the list of namespace parts and the class name
         - test_case_class - the fully-qualified PHP Class name
                             (string)"""
        parts = test_case_class.split('\\')
        class_name = parts.pop()
        return parts, class_name

    def parse_test_list(self, test_list_file, timing_data):
        """Process the output of phpunit's `--list-tests-xml` command
        and return a list of test classes with timing data
         - test_list_file - the path of XML file from phpunit (string)
         - timing_data - a dictionary mapping test classes to test
               durations (per ResultCacheParser.parse_result_cache)
        """
        tests_xml = ET.parse(test_list_file)
        tests = []
        for test_case_class in tests_xml.findall('testCaseClass'):
            test_name = test_case_class.get("name")
            namespace, class_name = self.extract_namespace(test_name)
            last_run_time = timing_data.get(test_name, None)
            tests.append((class_name, namespace, last_run_time))
        return tests


class FilesystemScanner:
    """Scan the filesystem for PHP files, excluding the `vendor`
    folder and `ParserIntegrationTest.php`"""

    def __init__(self, project_dir):
        """Create the FilesystemScanner
        - project_dir - the root of the project (string)"""
        self.project_dir = project_dir

    def scan_directory_for_php_files(self, directory):
        """Search in the provided directory for PHP files
        - directory - the path to scan (string)"""
        php_files = {}
        # We exclude ParserIntegrationTest and SandboxTest from the
        # scan here. ParserIntegrationTest is a dynamic test suite
        # that generates a lot of tests that cannot be split into
        # smaller chunks, and SandboxTest generates a suite of dynamic
        # tests (which seem to be skipped in CI) (see T345481)
        ignore_list = [
            "vendor",
            "ParserIntegrationTest.php",
            "SandboxTest.php",
        ]
        for root, dirs, files in os.walk(directory):
            # Filter out unwanted directories
            dirs[:] = [d for d in dirs if d not in ignore_list]
            for file in files:
                # We're only intersted in Test classes here. Suites should
                # be expanded by the `--list-tests-xml` operation
                if file.endswith('Test.php') and file not in ignore_list:
                    filename = os.path.basename(file)
                    if filename not in php_files:
                        php_files[filename] = []
                    php_files[filename].append(os.path.join(root, file))
        return php_files

    def extract_namespace_from_file(self, filename):
        """Extract the namespace declaration from the provided file
        - filename - path to a PHP file (string)"""
        with open(filename, 'r') as file:
            contents = file.read()
        matches = re.search(r'\bnamespace\s+([^\s;]+)', contents)
        if matches:
            return matches.group(1).split('\\')
        return []

    def resolve_correct_file(self, test_class, namespace_array, php_files):
        """Given a PHP class name, its namespace, and a list of PHP files,
        return the path to the PHP file that defines the class (there may
        be more than one class with the same name in the project, but the
        namespace::classname combination should be unique).
         - test_class - the name of the PHP class (string)
         - namespace_array - an array of parts of the namespace (string array)
         - php_files - an array of paths of PHP files (string array)
        """
        filename = test_class + ".php"
        if filename not in php_files:
            # No filesystem PHP file matches the provided class name
            logger.info("No same-named file found for class %s", filename)
            return None
        if len(php_files[filename]) == 1:
            return php_files[filename][0]
        for file in php_files[filename]:
            namespace = self.extract_namespace_from_file(file)
            if namespace == namespace_array:
                return file
        # None of the namespaces extracted from matching PHP files
        # matched the provided namespace
        logger.info("No namespace match found for %s", test_class)
        return None

    def find_test_files(self, tests):
        """Given a list of test classes, return a list of paths of the
        PHP files on the filesystem that define those test classes
         - tests - an array of [ class_name, [ namespace parts ] ]"""
        php_files = self.scan_directory_for_php_files(self.project_dir)
        test_files = []
        seen_paths = []
        for test in tests:
            resolved_path = self.resolve_correct_file(
                test[0], test[1], php_files
            )
            if resolved_path not in seen_paths:
                test_files.append(
                    (
                        resolved_path,
                        test[2],
                    )
                )
                seen_paths.append(resolved_path)
        return test_files


class SuiteBuilder:
    """Take a list of test classes annotated with their runtime, and
    return a (balanced) list of suites that are made up of chunks
    of the whole list of tests.
    """

    def smallest_group(self, suites):
        """Return the index of the suite with the least cumulative test
        time"""
        min_time = float('inf')
        min_index = 0
        for i, suite in enumerate(suites):
            if suite["time"] < min_time:
                min_time = suite["time"]
                min_index = i
        return min_index

    def make_suites(self, test_list, groups):
        """Turn the list of tests into an array of 'suites'
        - test_list - the list of tests in the format [filename, time]
        - groups - the number of buckets to split into (int)"""
        suites = [{"list": [], "time": 0} for _ in range(groups)]
        round_robin = 0
        test_list.sort(
            key=lambda x: x[1] if x[1] is not None else float('inf'),
            reverse=True,
        )
        for filename, time in test_list:
            if time is None:
                time = 0
            if time == 0:
                next_suite = round_robin
                round_robin = (round_robin + 1) % groups
            else:
                next_suite = self.smallest_group(suites)
            suites[next_suite]["list"].append(filename)
            suites[next_suite]["time"] += time
        return suites


class PhpUnitXmlManager:
    """Create a `phpunit.xml` file by parsing the contents of
    `phpunit.xml.dist`, adding additional test suites, and writing
    back out to `phpunit.xml`"""

    def __init__(self, project_dir):
        self.project_dir = project_dir

    def generate_phpunit_xml(self, suites):
        """Generate the `phpunit.xml` output on the basis of
        `phpunit.xml.dist`, adding the provided suites to the list
        of testsuites
         - suites - the suites to add, in the format [
             "list" => [filenames], "time" => time
           ] (per SuiteBuilder.make_suites)
        """
        phpunit_xml = ET.parse(
            os.path.join(self.project_dir, "phpunit.xml.dist")
        )
        root = phpunit_xml.getroot()
        groups = len(suites)
        for i, suite in enumerate(suites):
            testsuite = ET.SubElement(
                root.find("testsuites"),
                "testsuite",
                {"name": f"split_group_{i}"},
            )
            for filename in suite["list"]:
                if filename:
                    ET.SubElement(testsuite, "file").text = filename
            if i == 0:
                # Add SandboxTest back here. It will be skipped, but
                # should be included here for completeness.
                ET.SubElement(testsuite, "file").text = (
                    "extensions/Scribunto/tests/phpunit/Engines/"
                    "LuaSandbox/SandboxTest.php"
                )
        testsuite = ET.SubElement(
            root.find("testsuites"),
            "testsuite",
            {"name": f"split_group_{groups}"},
        )
        # Add the ExtensionsParserTestSuite back here
        ET.SubElement(
            testsuite, "file"
        ).text = "tests/phpunit/suites/ExtensionsParserTestSuite.php"
        xml_str = parseString(
            ET.tostring(root, encoding='utf-8')
        ).toprettyxml()
        trimmed = '\n'.join(
            [line for line in xml_str.split('\n') if line.strip()]
        )
        with open(
            os.path.join(self.project_dir, "phpunit.xml"), "w"
        ) as xml_file:
            xml_file.write(trimmed)


class Splitter:
    """Using as its inputs the list of tests generated by PHPUnit's
    `--list-test-xml`, a number of groups, and optionally a PHPUnit
    results cache file, create a `phpunit.xml` file the extends the
    existing `phpunit.xml.dist` with additional test suites based on
    splitting the list of tests evenly over a number of buckets."""

    def __init__(self, project_dir):
        self.project_dir = project_dir

    def split(self, xml_file, group_count, cache_file):
        """Split the provided xml file
        - xml_file - path to the `--list-test-xml` output (string)
        - group_count - the number of groups (int)
        - cache file - path to the `.phpunit.result.cache` file (string)"""
        timing_data = {}
        if cache_file is not None:
            print("Using results cache file", cache_file)
            timing_data = ResultCacheParser().parse_result_cache(cache_file)
        tests = TestListParser().parse_test_list(xml_file, timing_data)
        test_files = FilesystemScanner(self.project_dir).find_test_files(tests)
        suites = SuiteBuilder().make_suites(test_files, group_count)
        phpunitxml_manager = PhpUnitXmlManager(self.project_dir)
        phpunitxml_manager.generate_phpunit_xml(suites)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Supply a test xml file")
        sys.exit(1)

    if len(sys.argv) < 3:
        print("Specify a number of groups")
        sys.exit(1)

    cache_file = None
    if len(sys.argv) == 4:
        cache_file = sys.argv[3]

    Splitter(os.getcwd(), os.getcwd()).split(
        sys.argv[1], int(sys.argv[2]), cache_file
    )
