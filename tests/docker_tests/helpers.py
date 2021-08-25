from textwrap import dedent
from pathlib import PurePath, Path
from shell_adventure.docker_side.tutorial_docker import TutorialDocker

__all__ = [
    "SIMPLE_PUZZLES",
    "setup_tutorial",
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
            checker = checker
        )
""")

def setup_tutorial(tutorial: TutorialDocker, working_dir: Path, **setup):
    """
    Calls setup on TutorialDocker. Pass args that will be passed to setup().
    Provides some default for setup() args, sets tutorial.home to working_dir
    """
    default_setup = {
        "home": working_dir,
        "user": None, # Default to container's user
        "setup_scripts": {},
        "modules": {PurePath("puzzles.py"): SIMPLE_PUZZLES},
        "puzzles": ["puzzles.move"],
        "name_dictionary": "apple\nbanana\n",
        "content_sources": [],
        "send_checkers": True,
    }
    setup = {**default_setup, **setup} # merge
    tutorial.setup(**setup)
