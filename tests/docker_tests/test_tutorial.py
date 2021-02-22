from typing import *
import pytest
from pytest import mark
from shell_adventure_docker.tutorial import Tutorial
import yaml, json, os, subprocess
from textwrap import dedent;

# @mark.filterwarnings("ignore:Using or importing the ABCs from")
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

class TestTutorial:
    # TODO maybe spin up a container for the tutorial? But then I can't access the Tutorial object.
    # I could start a python session in the container or run the tests in the container.

    @staticmethod
    def _create_tutorial(tmp_path, puzzles: Dict[str, str], config: str, bash_pid: int = None) -> Tutorial:
        """
        Creates a tutorial with the given puzzles and config strings.
        Config will be saved to tmp_path/myconfig.py, puzzles will be saved to the dictionary key names under tmp_path.
        cd's into a temporary directory before running the puzzles. These tests are running on the host machine so don't do
        anything crazy in the puzzle generation functions.
        """
        (tmp_path / "modules").mkdir()
        for name, content in puzzles.items():
            (tmp_path / "modules" / name).write_text(content)
        config_file = tmp_path / "myconfig.yaml"
        # I'm converting the YAML to JSON since he normal config is in YAML but then converted to JSON
        # before being put in the docker container for the Tutorial to read.
        config_file.write_text(json.dumps(yaml.safe_load(config)))

        working_dir = tmp_path / "home"
        working_dir.mkdir()
        os.chdir(working_dir)

        tutorial = Tutorial(config_file, bash_pid)
        return tutorial

    def test_creation(self, tmp_path):
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, f"""
            modules:
                - {tmp_path / "mypuzzles.py"}
            puzzles:
                - mypuzzles.move
        """)

        # Should contain the default module and my module
        assert set(tutorial.modules.keys()) == {"mypuzzles"}
        assert {m.__name__ for m in tutorial.modules.values()} == {"mypuzzles"}

        assert "mypuzzles.move" in tutorial.generators
        assert tutorial.puzzles[0].generator == "mypuzzles.move" # Not generated yet
        assert tutorial.puzzles[0].puzzle == None # Not generated yet

    def test_relative_path_creation(self, tmp_path):
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, SIMPLE_TUTORIAL)
        tutorial = Tutorial(f"{tmp_path / 'myconfig.yaml'}") # Strings should also work for path
        assert tutorial.config_file == tmp_path / "myconfig.yaml"
        assert "mypuzzles.move" in tutorial.generators

    def test_multiple_modules(self, tmp_path):
        tutorial = TestTutorial._create_tutorial(tmp_path, {
            "mypuzzles1.py": SIMPLE_PUZZLES,
            "mypuzzles2.py": SIMPLE_PUZZLES,
        }, """
            modules:
                - mypuzzles1.py
                - mypuzzles2.py
            puzzles:
                - mypuzzles1.move
        """)

        assert "mypuzzles1.move" in tutorial.generators
        assert "mypuzzles2.move" in tutorial.generators

    def test_missing_files(self, tmp_path):
        with pytest.raises(AssertionError, match="Unknown puzzle generator"):
            tutorial = TestTutorial._create_tutorial(tmp_path, {}, SIMPLE_TUTORIAL) # Don't make any puzzle files
        with pytest.raises(FileNotFoundError):
            tutorial = Tutorial(tmp_path / "not_a_config_file.yaml")

    def test_missing_puzzle(self, tmp_path):
        with pytest.raises(AssertionError, match="Unknown puzzle generator mypuzzles.not_a_puzzle"):
            tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, """
                modules:
                    - mypuzzles.py
                puzzles:
                    - mypuzzles.not_a_puzzle
            """)

    def test_private_methods_arent_puzzles(self, tmp_path):
        puzzles = dedent("""
            def _private_method():
                return "not a puzzle"

            my_lambda = lambda: "not a puzzle"

            def move():
                return Puzzle(
                    question = f"Easiest puzzle ever.",
                    checker = lambda: True,
                )
        """)

        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": puzzles}, SIMPLE_TUTORIAL)
        assert list(tutorial.generators.keys()) == ["mypuzzles.move"]

    def test_solve_puzzle(self, tmp_path):
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, SIMPLE_TUTORIAL)
        tutorial.run()
        puzzle = tutorial.puzzles[0].puzzle

        assert tutorial.solve_puzzle(puzzle) == (False, "Incorrect!")
        assert puzzle.solved == False

        os.system("cp A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle) == (False, "Incorrect!")

        os.system("mv A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle) == (True, "Correct!")
        assert puzzle.solved == True

    def test_solve_puzzle_feedback(self, tmp_path):
        puzzles = dedent("""
            def unsolvable():
                return Puzzle(
                    question = f"You can never solve this puzzle.",
                    checker = lambda: "Unsolvable!",
                )
        """)
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": puzzles}, """
            modules:
                - mypuzzles.py
            puzzles:
                - mypuzzles.unsolvable
        """)
        tutorial.run()
        puzzle = tutorial.puzzles[0].puzzle

        assert tutorial.solve_puzzle(puzzle) == (False, "Unsolvable!")
        assert puzzle.solved == False

    def test_solve_puzzle_error(self, tmp_path):
        puzzles = dedent("""
            def invalid():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: 100,
                )
        """)
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": puzzles}, """
            modules:
                - mypuzzles.py
            puzzles:
                - mypuzzles.invalid
        """)
        tutorial.run()

        puzzle = tutorial.puzzles[0].puzzle
        with pytest.raises(Exception, match="bool or str expected"):
            tutorial.solve_puzzle(puzzle)

    def test_student_cwd(self, tmp_path):
        bash = subprocess.Popen(["bash", "-c", "sleep 4"], cwd = tmp_path)
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, SIMPLE_TUTORIAL, bash.pid)
        assert tutorial.student_cwd() == tmp_path
        bash.kill()

    def test_student_cwd_spaces(self, tmp_path):
        dir = (tmp_path / " ")
        dir.mkdir()

        bash = subprocess.Popen(["bash", "-c", "sleep 4"], cwd = dir)
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, SIMPLE_TUTORIAL, bash.pid)
        assert tutorial.student_cwd() == dir
        bash.kill()

    # TODO test checker functions with different args.