
from typing import Dict, Union, List
from textwrap import dedent
from shell_adventure.tutorial import Tutorial

SIMPLE_PUZZLES = dedent("""
    from shell_adventure_docker import *

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

def run_command(tutorial: Tutorial, command: Union[str, List[str]]):
    """ Execute a command in a tutorial, make a commit after the command. """
    # I tried using an actual bash session so we could test if the script was getting called
    # but I couldn't get bash to run PROMPT_COMMAND when called via Popen. Using the bash `-i`
    # flag doesn't work either.
    tutorial.container.exec_run(command)
    tutorial.commit()

def file_exists(tutorial: Tutorial, file: str): 
    """ Checks if a file exists in the container. """
    exit_code, output = tutorial.container.exec_run(["test", "-f", file])
    return exit_code == 0 # file exists