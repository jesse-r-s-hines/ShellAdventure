#!/bin/bash
docker build -t shell-adventure . 1> /dev/null && # Only print errors

echo "=========== mypy analysis ==========="
mypy shell_adventure shell_adventure_docker tests

echo -e "\n"
echo "Main tests"
python3.7 -m pytest --cov --cov-report html --cov-report term

echo -e "\n"
echo "Tests in Docker container"
docker run -t --user="root" shell-adventure pytest --cov=shell_adventure_docker --cov-report term /usr/local/shell_adventure_docker_tests