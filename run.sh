#!/bin/bash
docker build -t shell-adventure docker_image 1> /dev/null && # Only print errors
source .venv/bin/activate
.venv/bin/python3.7 launch.py examples/example_config.yaml 