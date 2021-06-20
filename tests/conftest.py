pytest_plugins = ['helpers_namespace']
import pytest

from typing import Dict, Union, List
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

@pytest.helpers.register #type: ignore
def run_command(tutorial: Tutorial, command: Union[str, List[str]]):
    """ Execute a command in a tutorial, make a commit after the command. """
    # I tried using an actual bash session so we could test if the script was getting called
    # but I couldn't get bash to run PROMPT_COMMAND when called via Popen. Using the bash `-i`
    # flag doesn't work either.
    tutorial.container.exec_run(command)
    tutorial.commit()

@pytest.helpers.register #type: ignore
def file_exists(tutorial: Tutorial, file: str): 
    """ Checks if a file exists in the container. """
    exit_code, output = tutorial.container.exec_run(["test", "-f", file])
    return exit_code == 0 # file exists