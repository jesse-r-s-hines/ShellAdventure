#!/bin/bash
docker build -t shell-adventure docker 1> /dev/null &&
python3.7 -m shell_adventure.tutorial shell_adventure/tutorials/default.yaml 