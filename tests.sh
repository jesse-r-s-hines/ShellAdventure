#!/bin/bash
set -e # Exit script if any command fails

docker build -t shell-adventure docker_image 1> /dev/null # Only print errors
for dockerfile in tests/docker_images/Dockerfile.tests.*; do # Build all Dockerfiles in tests/docker_images
    tag=${dockerfile##*.} # Removes all but last extension of dockerfile
    docker build -t shell-adventure/tests:$tag --file $dockerfile docker_image 1> /dev/null
done

source .venv/bin/activate

echo "=========== mypy analysis ==========="
mypy shell_adventure shell_adventure_docker shell_adventure_shared tests

set +e # Undo "set -e"

echo -e "\n\n"
echo "Tests in Docker container"
.venv/bin/python3.7 -m tests.run_docker_tests $@

echo -e "\n\n"
echo "Main tests"
.venv/bin/python3.7 -m pytest $@

# See https://docs.pytest.org/en/documentation-restructure/how-to/usage.html#possible-exit-codes for meaning of pytest exit codes
