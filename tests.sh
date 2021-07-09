#!/bin/bash
set -e # Exit script if any command fails

docker build -t shell-adventure docker_image 1> /dev/null # Only print errors
for dockerfile in tests/docker_images/Dockerfile.tests.*; do # Build all Dockerfiles in tests/docker_images
    tag=${dockerfile##*.} # Removes all but last extension of dockerfile
    docker build -t shell-adventure/tests:$tag --file $dockerfile docker_image 1> /dev/null
done

source .venv/bin/activate

echo "=========== mypy analysis ==========="
mypy shell_adventure tests

set +e # Undo "set -e"

echo -e "\n\n"
echo "Tests in Docker container"
# Also makes a ".coverage" report in cwd
.venv/bin/python3.7 -m tests.run_docker_tests $@


echo -e "\n\n"
echo "Main tests"
# Merge coverage report with report from container
.venv/bin/python3.7 -m pytest --cov --cov-report= --cov-append $@

# Output html report
# Coverage reports are somewhat incomplete as we don't have a good way to track the code that gets run in the container
# during integration tests, since the container is launched and closed during the test.
coverage html
