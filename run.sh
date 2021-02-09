#!/bin/bash
docker build -t shell-adventure . 1> /dev/null && # Only print errors
python3.7 -m shell_adventure.shell_adventure shell_adventure/tutorials/default.yaml 