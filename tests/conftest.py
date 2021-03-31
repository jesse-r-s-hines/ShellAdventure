pytest_plugins = ['helpers_namespace']
import pytest

from typing import Dict
from shell_adventure.tutorial import Tutorial

# Defines some fixtures for use in the rest of the tests

@pytest.helpers.register #type: ignore
def create_tutorial(tmp_path, files: Dict[str, str]) -> Tutorial:
    """
    Creates a tutorial with the given files. 
    Files (such as puzzles) will be saved to the dictionary key names
    under tmp_path with the matching content in the dictionary.
    The config file should be saved under the key "config.yaml"
    """

    for file, content in files.items():
        path = tmp_path / file
        path.parent.mkdir(parents = True, exist_ok = True)
        path.write_text(content)

    return Tutorial(tmp_path / "config.yaml")