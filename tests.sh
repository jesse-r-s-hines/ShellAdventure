#!/bin/bash
set -e # Exit script if any command fails

# Build the image locally. Then build the shelladventure/tests:main and other test images. We'll use that
# tests:main image in our actual tests unless specified otherwise so that the tests are using our local
# version of the image instead of pulling the one on DockerHub
docker build -t shelladventure/shell-adventure:latest docker_image 1> /dev/null # Only print errors
for dockerfile in tests/docker_images/Dockerfile.tests.*; do # Build all Dockerfiles in tests/docker_images
    tag=${dockerfile##*.} # Removes all but last extension of dockerfile
    docker build -t shelladventure/tests:$tag --file $dockerfile tests/docker_images 1> /dev/null
done

source .venv/bin/activate

echo "=========== mypy analysis ==========="
mypy shell_adventure tests

set +e # Undo "set -e"

echo -e "\n\n"
echo "Tests in Docker container"
# Also makes a ".coverage" report in cwd
python3 -m tests.run_docker_tests $@


echo -e "\n\n"
echo "Main tests"
# Merge coverage report with report from container
python3 -m pytest --cov --cov-report= --cov-append $@

# Output html report
# Coverage reports are somewhat incomplete as we don't have a good way to track the code that gets run in the container
# during integration tests, since the container is launched and closed during the test.
coverage html
