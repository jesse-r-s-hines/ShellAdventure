pytest_plugins = ['helpers_namespace']
import pytest

from typing import Dict
from shell_adventure.tutorial import Tutorial

# Defines some fixtures for use in the rest of the tests

@pytest.helpers.register
def create_tutorial(tmp_path, puzzles: Dict[str, str], config: str) -> Tutorial:
    """
    Creates a tutorial with the given puzzles and config strings.
    Config will be saved to tmp_path/config.yaml, puzzles will be saved to the dictionary key names under tmp_path.
    """
    for name, content in puzzles.items():
        (tmp_path / name).write_text(content)
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config)

    tutorial = Tutorial(config_file)
    return tutorial