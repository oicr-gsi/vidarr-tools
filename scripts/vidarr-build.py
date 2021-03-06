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

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--build-config",
    default="vidarrbuild.json",
    dest="build_config")
subparsers = parser.add_subparsers(dest="command")

build_parser = subparsers.add_parser(
    "build",
    help="Run the build process to produce a Vidarr-compatible workflow bundle.")

test_parser = subparsers.add_parser(
    "test", help="Build the workflow and perform the regression tests.")
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

for (workflow_key, workflow_parser) in workflow_types.items():
    if workflow_key in config:
        if not isinstance(config[workflow_key], str):
            sys.stderr.write(
                f"The `{workflow_key}` property must contain the name of the root workflow file.\n")
            sys.exit(1)
        file_path = os.path.join(
            os.path.dirname(
                args.build_config),
            config[workflow_key])
        if not os.path.exists(file_path):
            sys.stderr.write(f"Cannot find {file_path}.")
            sys.exit(1)

        workflows.append(lambda: workflow_parser(file_path))

if len(workflows) != 1:
    sys.stderr.write(
        "The configuration file must have exactly one root workflow.")
    sys.exit(1)

workflow = workflows[0]()

if not workflow:
    sys.exit(1)

with open("v.out", "w") as f:
    json.dump(workflow, f)

if args.command == "build":
    sys.exit(0)

tests = [
    os.path.join(
        os.path.dirname(
            args.build_config),
        "vidarrtest-regression.json")]

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

for test in tests:
    print(f"Running tests from {test}...")
    sys.stdout.flush()
    sys.stderr.flush()
    subprocess.check_call(
        ["vidarr", "test", "-c", args.test_config, "-w", "v.out", "-t", test])

ok = True
for registration_url in registration_urls:
    print(f"Pushing to {registration_url} server...")
    res = requests.post(registration_url, json=workflow)
    if res.status_code not in [200, 201, 409]:
        print(
            f"Failed to register workflow version on {registration_url}: response status {res.status_code}")
        if res.content:
            print(f"{res.json()}") # only read the response body if it is not empty
        ok = False
    elif res.status_code in [409]:
        print(f"This workflow version is different from the workflow version with the same name + version on {registration_url}")
        ok = False
    elif res.status_code in [200]:
        print(f"Workflow version is already registered on {registration_url}")
        registered = True
    else:
        print(f"Registered on {registration_url}!")
        registered = True

if ok:
    print("EVERYTHING IS AWESOME!!!")
    sys.exit(0)
else:
    print("Awesomeness was a pipedream")
    sys.exit(1)
