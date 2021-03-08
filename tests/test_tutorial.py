#TODO
from typing import *
import pytest
from pytest import mark
from shell_adventure.tutorial import Tutorial
import yaml, json, os, subprocess
from textwrap import dedent;

#TODO make this use File etc.
SIMPLE_PUZZLES = dedent("""
    from os import system

    def move():
        system("echo 'move1' > A.txt")

        def checker():
            aCode = system("test -f A.txt")
            bCode = system("test -f B.txt")
            return (aCode >= 1) and (bCode == 0)

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker
        )
""")
SIMPLE_TUTORIAL = """
    modules:
        - mypuzzles.py
    puzzles:
        - mypuzzles.move
"""

# Test creating a tutorial (just parsing the config)
# Test creating the tutorial bad config and various config

# integration, start tutorial, check stuff, solve puzzle, connect to bash?, stop check container gone.

class TestTutorial:
    @staticmethod
    def _create_tutorial(tmp_path, puzzles: Dict[str, str], config: str) -> Tutorial:
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

    def test_creation(self, tmp_path):
        tutorial = TestTutorial._create_tutorial(tmp_path, {"puzzle1.py": SIMPLE_PUZZLES, "puzzle2.py": SIMPLE_PUZZLES}, f"""
            modules:
                - puzzle1.py # Relative path
                - {tmp_path / "puzzle2.py"} # Absolute path
            puzzles:
                - puzzle1.move
                - puzzle2.move
        """)
        assert tutorial.data_dir == tmp_path

        # Should contain the default module and my module
        assert {m.resolve() for m in tutorial.module_paths} == {tmp_path / "puzzle1.py", tmp_path / "puzzle2.py"}
        assert {pt.generator for pt in tutorial.puzzles} == {"puzzle1.move", "puzzle2.move"}

    def test_str_path_creation(self, tmp_path):
        # Create the files
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, SIMPLE_TUTORIAL)
        tutorial = Tutorial(f"{tmp_path / 'config.yaml'}") # Strings should also work for path
        assert tutorial.config_file == tmp_path / "config.yaml"

    def test_empty(self, tmp_path):
        with pytest.raises(Exception, match="Invalid config"):
            tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, "")

    def test_missing_files(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            tutorial = TestTutorial._create_tutorial(tmp_path, {}, SIMPLE_TUTORIAL) # Don't make any puzzle files
        with pytest.raises(FileNotFoundError):
            tutorial = Tutorial(tmp_path / "not_a_config_file.yaml")

    def test_duplicate_module_names(self, tmp_path):
        with pytest.raises(Exception, match='Multiple puzzle modules with name "puzzle1.py" found'):
            tutorial = TestTutorial._create_tutorial(tmp_path, {"puzzle1.py": SIMPLE_PUZZLES}, """
                modules:
                    - puzzle1.py
                    - puzzle1.py
                puzzles:
                    puzzle1.move
            """) 
    # Integration tests, running the tutorial and container.
