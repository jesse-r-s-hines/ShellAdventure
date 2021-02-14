#!/bin/bash
mypy shell_adventure tests
python3.7 -m pytest --cov --cov-report html --cov-report term $@