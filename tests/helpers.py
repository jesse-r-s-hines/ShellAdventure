
from typing import Dict, Tuple, Union, List
from textwrap import dedent
from pathlib import Path
from shell_adventure.host_side.tutorial import Tutorial

__all__ = [
    "SIMPLE_PUZZLES",
    "SIMPLE_TUTORIAL",
    "create_tutorial",
    "run_command",
    "file_exists",
]

SIMPLE_PUZZLES = dedent("""
    from shell_adventure.api import *

    def move():
        file = File("A.txt")
        file.write_text("A")

        def checker():
            return not file.exists() and File("B.txt").exists()

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker,
            score = 2,
        )

    def move2():
        file = File("C.txt")
        file.write_text("C")

        def checker():
            return not file.exists() and File("D.txt").exists()

        return Puzzle(
            question = f"Rename C.txt to D.txt",
            checker = checker,
            score = 3,
        )
""")

SIMPLE_TUTORIAL = dedent("""
    modules:
        - mypuzzles.py
    puzzles:
        - mypuzzles.move
""")

def create_tutorial(tmp_path: Path, files: Dict[str, str]) -> Tutorial:
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

def run_command(tutorial: Tutorial, cmd: Union[str, List[str]],  **kwargs) -> Tuple[int, str]:
    """ Execute a command in a tutorial, return the exit code and output """
    exit_code, output = tutorial.container.exec_run(cmd, **kwargs)
    return (exit_code, output.decode().strip())

def file_exists(tutorial: Tutorial, file: str): 
    """ Checks if a file exists in the container. """
    exit_code, output = tutorial.container.exec_run(["test", "-f", file])
    return exit_code == 0 # file exists