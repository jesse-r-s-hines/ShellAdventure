#!/bin/bash
docker build -t shell-adventure . 1> /dev/null && # Only print errors
mypy shell_adventure shell_adventure_docker tests
echo "Running tests in docker container..."
docker run -t --user="root" shell-adventure pytest /usr/local/shell_adventure_docker/tests
python3.7 -m pytest --cov --cov-report html --cov-report term $@