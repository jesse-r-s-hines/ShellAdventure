#!/bin/bash
docker build -t shell-adventure . 1> /dev/null # Only print errors
docker build -t shell-adventure:test --build-arg TESTING=1 . 1> /dev/null # Only print errors

source .venv/bin/activate

echo "=========== mypy analysis ==========="
mypy shell_adventure shell_adventure_docker tests

# See https://docs.pytest.org/en/documentation-restructure/how-to/usage.html#possible-exit-codes for meaning of pytest exit codes
echo -e "\n\n"
echo "Main tests"
.venv/bin/python3.7 -m pytest --cov --cov-report term

TEST_DIR=/usr/local/shell_adventure_docker_tests
echo -e "\n\n"
echo "Tests in Docker container"
docker run -t --rm --user="root" --workdir="$TEST_DIR" shell-adventure:test pytest --cov=shell_adventure_docker --cov-report term "$TEST_DIR"
