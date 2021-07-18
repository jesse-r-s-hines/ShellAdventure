#!/usr/bin/env python3
from typing import List
from pathlib import Path
import sys, subprocess
import shell_adventure
from shell_adventure.host_side import docker_helper

PROJ_PATH = shell_adventure.PKG_PATH.parent
args = sys.argv[1:]

def header(message: str):
    # Using flush fixes an issue in GitHub actions where prints and output from subprocesses get out of order in the report
    print(f"\n{f' {message} '.center(45, '=')}\n", flush = True)
def run(command: List[str]):
    return subprocess.run(command, stdout=sys.stdout).returncode

header("Building Images")
# Build the docker image locally (in case it has been modified locally since last release)
(image, log) = docker_helper.client.images.build(
    path = str(PROJ_PATH / "docker_image"),
    dockerfile = "Dockerfile",
    tag = f"shelladventure/tests:v1",
    rm = True, # Remove intermediate containers
)
image.tag(f"shelladventure/tests:latest")

# Build all the images in tests/docker_images
for dockerfile in PROJ_PATH.glob("tests/docker_images/Dockerfile.tests.*"):
    tag = dockerfile.suffix[1:]
    docker_helper.client.images.build(
        path = str(PROJ_PATH / "tests/docker_images"),
        dockerfile = str(dockerfile.name),
        tag = f"shelladventure/tests:{tag}",
        rm = True, # Remove intermediate containers
    )
print("Done!", flush = True)

header("MyPy Analysis")

assert run(["mypy"]) == 0 # quit if mypy fails


header("Tests in Docker Container")
# Also makes a ".coverage" report in cwd
dockerTests = run(["python3", "-m", "tests.run_docker_tests", *args])

header("Main Tests")
# Merge coverage report with report from container
mainTests = run(["python3", "-m", "pytest", "--cov", "--cov-report=", "--cov-append", *args])


# Output html report
# Coverage reports are somewhat incomplete as we don't have a good way to track the code that gets run in the container
# during integration tests, since the container is launched and closed during the test.
run(["coverage", "html"])

exit(0 if dockerTests == 0 and mainTests == 0 else 1)
