#!/bin/bash
docker build -t shell-adventure docker_image 1> /dev/null # Only print errors
docker build -t shell-adventure/tests:main --file tests/docker_images/Dockerfile.tests.main docker_image 1> /dev/null # Only print errors
docker build -t shell-adventure/tests:alpine --file tests/docker_images/Dockerfile.tests.alpine docker_image 1> /dev/null # Only print errors

source .venv/bin/activate

echo "=========== mypy analysis ==========="
mypy shell_adventure shell_adventure_docker shell_adventure_shared tests

# See https://docs.pytest.org/en/documentation-restructure/how-to/usage.html#possible-exit-codes for meaning of pytest exit codes
echo -e "\n\n"
echo "Main tests"
.venv/bin/python3.7 -m pytest $@

echo -e "\n\n"
echo "Tests in Docker container"
.venv/bin/python3.7 -m tests.run_docker_tests $@