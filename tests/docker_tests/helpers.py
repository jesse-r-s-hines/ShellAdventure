from textwrap import dedent
from pathlib import PurePath
from shell_adventure_docker.tutorial_docker import TutorialDocker

SIMPLE_PUZZLES = dedent("""
    from shell_adventure_docker import *

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

def create_tutorial(working_dir, **setup) -> TutorialDocker:
    """
    Factory for TutorialDocker. Pass args that will be passed to setup().
    Provides some default for setup() args
    tutorial.home to working_dir
    """
    default_setup = {
        "home": working_dir,
        "user": "student",
        "resources": {},
        "setup_scripts": [],
        "modules": {PurePath("puzzles.py"): SIMPLE_PUZZLES},
        "puzzles": ["puzzles.move"],
        "name_dictionary": "apple\nbanana\n",
        "content_sources": [],
    }
    setup = {**default_setup, **setup} # merge

    tutorial = TutorialDocker()
    tutorial.setup(**setup)

    return tutorial