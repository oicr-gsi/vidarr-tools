#!/usr/bin/env python3

import argparse
import json
import os
from typing import List
import requests
import subprocess
import sys
import vidarr.wdl

# In the future, other workflow languages should be added here.
workflow_types = {
    "wdl": vidarr.wdl.parse
}


# CustomArgumentParser extends argparse.ArgumentParser, to help parse any argument in command line.
# Default is "vidarrbuild.json", and the value is stored in 'build_config'.
class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(CustomArgumentParser, self).__init__(*args, **kwargs)
        self.build_config_arg = self.add_argument(
            "-c",
            "--build-config",
            default="vidarrbuild.json",
            dest="build_config")


# Create an instance of the custom argument parser
parser = CustomArgumentParser()

# looks like this:
# {
#    "names": [
#        "myworkflow"
#    ],
#    "wdl": "myworkflow.wdl"
# }
#
subparsers = parser.add_subparsers(dest="command")

build_parser = subparsers.add_parser(
    "build",
    help="Run the build process to produce a Vidarr-compatible workflow bundle.")

# This looks unused, but it's not so much unused as implicitly the default
test_parser = subparsers.add_parser(
    "test", help="Build the workflow and perform the regression tests.")

# https://github.com/oicr-gsi/vidarr/blob/master/admin-guide.md#creating-a-development-environment
test_parser.add_argument(
    "-t",
    "--test-config",
    dest="test_config",
    required=True,
    help="Vidarr plugin configuration file for running tests.",
    default=os.environ.get(
        "VIDARR_TEST_CONFIG",
        None))
test_parser.add_argument(
    "-p",
    "--performance-test",
    dest="performance_test",
    help="Run performance tests too.")

test_parser.add_argument(
    "-o",
    "--output-directory",
    dest="output_directory",
    help="Provide an explicit output directory for the test output files.")

deploy_parser = subparsers.add_parser(
    "deploy",
    help="Build the workflow, run the regression tests, and deploy the workflow to Vidarr servers.")

deploy_parser.add_argument(
    "-t",
    "--test-config",
    dest="test_config",
    required=True,
    help="Vidarr plugin configuration file for running tests.",
    default=os.environ.get(
        "VIDARR_TEST_CONFIG",
        None))
deploy_parser.add_argument(
    "-u",
    "--url",
    help="A Vidarr server to deploy to. If unspecified, the servers from the space-separated environment variable VIDARR_URLS will be used.",
    nargs='*',
    dest="vidarr_urls",
    default=[])
deploy_parser.add_argument(
    "-U",
    "--url-file",
    dest="vidarr_url_file",
    help="A file containing Vidarr servers to deploy to (one per line).")
deploy_parser.add_argument(
    "-p",
    "--performance-test",
    dest="performance_test",
    help="Run performance tests too.")
deploy_parser.add_argument(
    "-v",
    "--version",
    dest="version",
    help="The version number to push as.",
    required=True)

args = parser.parse_args()

if not args.command:
    sys.stderr.write(
        "Please supply a command: build, test, or deploy\n")
    sys.exit(1)

if not os.path.exists(args.build_config):
    sys.stderr.write(
        f"Cannot find {args.build_config}. Are you in the right directory?\n")
    sys.exit(1)

with open(args.build_config) as cf:
    config = json.load(cf)

if "names" not in config or not isinstance(config["names"], list) or any(
        not isinstance(n, str) for n in config["names"]) or not config["names"]:
    sys.stderr.write(
        "The `names` property must be present in the configuration file and contain a list of workflow names for deployment.\n")
    sys.exit(1)

workflows = []
# For each workflow type we know about (currently just WDL)
for (workflow_key, workflow_parser) in workflow_types.items():
    # Make sure a "wdl" field is in the build config
    if workflow_key in config:
        if not isinstance(config[workflow_key], str):
            sys.stderr.write(
                f"The `{workflow_key}` property must contain the name of the root workflow file.\n")
            sys.exit(1)
        # Get a path that looks like `/dir/where/vidarrbuild-dot-json/is/wdl`
        # die if it doesn't exist
        file_path = os.path.join(
            os.path.dirname(
                args.build_config),
            config[workflow_key])
        if not os.path.exists(file_path):
            sys.stderr.write(f"Cannot find {file_path}.")
            sys.exit(1)

        # Add wdl2vidarr as a lambda
        workflows.append(lambda: workflow_parser(file_path))

# Why do we specify 'root' workflow here?
if len(workflows) != 1:
    sys.stderr.write(
        "The configuration file must have exactly one root workflow.")
    sys.exit(1)

# Run the lambda we appended to workflows earlier
workflow = workflows[0]()

if not workflow:
    sys.exit(1)

# wdl2vidarr supports custom output file names, but vidarr-build is written with the assumption
# that there may be more than one parser, and who knows how the others would be implemented.
with open("v.out", "w") as f:
    json.dump(workflow, f)

# Exit early if command is 'build', don't try tests or deploying
if args.command == "build":
    sys.exit(0)

# Validate existence of vidarrtest-regression and vidarrtest-performance json files
# vidarrtest-regression is a JSON array of objects that looks like:
# [
#   {
#     "arguments": {
#       "contents": {
#         "configuration": "/path/to/test/data.fastq.gz",
#         "externalIds": [
#           {
#             "id": "TEST",
#             "provider": "TEST"
#           }
#         ]
#       },
#       "type": "EXTERNAL"
#     },
#     "description": "Tests that workflow does its thing",
#     "engineArguments": {
#       "write_to_cache": false,
#       "read_from_cache": false
#     },
#     "id": "myTest1",
#     "metadata": {
#       "contents": [
#         {
#           "outputDirectory": "/path/to/output/dir"
#         }
#       ],
#       "type": "ALL"
#       }
#     },
#     "validators": [
#        {
#         "metrics_calculate": "/path/to/calculate.sh",
#         "metrics_compare": "/path/to/compare.sh",
#         "output_metrics": "/path/to/output/metrics",
#         "type": "script"
#        }
#      ]
#   }
# ]
tests = [
    os.path.join(
        os.path.dirname(
            args.build_config),
        "vidarrtest-regression.json")]

# Appended to tests without modification and sent to Vidarr all the same - assume same format
if args.performance_test:
    tests.append(
        os.path.join(
            os.path.dirname(
                args.build_config),
            "vidarrtest-performance.json"))

for test in tests:
    if not os.path.exists(test):
        sys.stderr.write(f"Cannot find {test} containing required tests.\n")
        sys.exit(1)

# If 'deploy', validate the registration URLs and that those vidarrs have the workflow installed
registration_urls: List[str] = []
if args.command == "deploy":
    vidarr_urls: List[str] = []
    vidarr_urls.extend(filter(lambda x: bool(x), args.vidarr_urls))
    if args.vidarr_url_file:
        with open(args.vidarr_url_file, "r") as url_file:
            vidarr_urls.extend(
                filter(
                    lambda x: bool(x), map(
                        str.strip, url_file)))
    if not vidarr_urls:
        vidarr_urls.extend(
            filter(
                lambda x: bool(x),
                os.environ.get(
                    "VIDARR_URLS",
                    "").split(" ")))
    if not vidarr_urls:
        sys.stderr.write(
            "Cannot perform a deployment without a Vidarr server to update. Use --url or set VIDARR_URLS.\n")
        sys.exit(1)
    for vidarr_url in vidarr_urls:
        for name in config["names"]:
            res = requests.get(f"{vidarr_url}/api/workflow/{name}")
            if res.status_code != 200:
                print(
                    f"Workflow {name} not registered on {vidarr_url}. Skipping.")
                continue

            registration_urls.append(
                f"{vidarr_url}/api/workflow/{name}/{args.version}")
    if not registration_urls:
        print("""Could not find a server that wanted this workflow. :-(
        Check that the "names" in the vidarrbuild.json are registered on the servers or update the names.
        """)
        sys.exit(1)


# Actually run the tests. check_call() will kill the program if test's returncode is not 0
for test in tests:
    print(f"Running tests from {test}...")
    sys.stdout.flush()
    sys.stderr.flush()

    # Did the user provide an output directory? This runs vidarr-cli with the additional argument -o
    if args.output_directory is not None:
        print("Output directory provided")
        subprocess.check_call(
            ["vidarr", "test", "-c", args.test_config, "-w", "v.out", "-t", test, "-o", args.output_directory])
    else:
        print("No output directory provided")
        subprocess.check_call(
            ["vidarr", "test", "-c", args.test_config, "-w", "v.out", "-t", test])

# Assuming we didn't die from tests failing, deploy to each server
# `registration_urls` will be empty if our mode is not 'deploy'
ok = True
for registration_url in registration_urls:
    print(f"Pushing to {registration_url} server...")
    res = requests.post(registration_url, json=workflow)
    if res.status_code not in [200, 201, 409]:
        print(
            f"Failed to register workflow version on {registration_url}: response status {res.status_code}")
        if res.content:
            print(f"{res.json()}")  # only read the response body if it is not empty
        ok = False
    elif res.status_code in [409]:
        print(
            f"This workflow version is different from the workflow version with the same name + version on {registration_url}")
        ok = False
    elif res.status_code in [200]:
        print(f"Workflow version is already registered on {registration_url}")
        registered = True  # TODO unused?
    else:  # 201 means created
        print(f"Registered on {registration_url}!")
        registered = True

if ok:
    print("EVERYTHING IS AWESOME!!!")
    sys.exit(0)
else:
    print("Awesomeness was a pipedream")
    sys.exit(1)
