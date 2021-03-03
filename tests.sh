#!/bin/bash
docker build -t shell-adventure . 1> /dev/null # Only print errors
docker build -t shell-adventure:test -f Dockerfile.test . 1> /dev/null # Only print errors

echo "=========== mypy analysis ==========="
mypy shell_adventure shell_adventure_docker tests

# See https://docs.pytest.org/en/documentation-restructure/how-to/usage.html#possible-exit-codes for meaning of pytest exit codes

python3.7 -m pytest --collect-only $@ &> /dev/null
if [ "$?" -eq "4" ]; then # collection failed, unknown file, just run the docker tests
    echo "Skipping Main Tests"
else
    echo -e "\n\n"
    echo "Main tests"
    python3.7 -m pytest --cov --cov-report term $@
fi

TEST_DIR=/usr/local/shell_adventure_docker_tests
docker run --workdir="$TEST_DIR" shell-adventure:test pytest --collect-only "$TEST_DIR" $@ &> /dev/null
if [ "$?" -eq "4" ]; then # collection failed, unknown file, just run the main tests
    echo "Skipping tests in Docker container"
else
    echo -e "\n\n"
    echo "Tests in Docker container"
    docker run -t --user="root" --workdir="$TEST_DIR" shell-adventure:test pytest --cov=shell_adventure_docker --cov-report term "$TEST_DIR" $@
fi
