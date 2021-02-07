from typing import *
import pytest
from pytest import mark
from shell_adventure.tutorial import Tutorial

# @mark.filterwarnings("ignore:Using or importing the ABCs from")
SIMPLE_PUZZLES = """
def move(file_system):
    file_system.run_command("echo 'move1' > A.txt")

    def checker(file_system):
        aCode, _ = file_system.run_command("test -f A.txt")
        bCode, _ = file_system.run_command("test -f B.txt")
        return (aCode == 1) and (bCode == 0)

    return Puzzle(
        question = f"Rename A.txt to B.txt",
        checker = checker
    )
"""
SIMPLE_TUTORIAL = """
    modules:
        - mypuzzles.py
    puzzles:
        - mypuzzles.move
"""

class TestTutorial:
    def _create_tutorial(tmp_path, puzzles: Dict[str, str], config: str):
        """
        Creates a tutorial with the given puzzles and config strings.
        Config will be saved to tmp_path/myconfig.py, puzzles will be saved to the dictionary key names under tmp_path.
        """
        for name, content in puzzles.items():
            (tmp_path / name).write_text(content)
        config_file = tmp_path / "myconfig.yaml"
        config_file.write_text(config)
        tutorial = Tutorial(config_file)
        return tutorial

    def test_creation(self, tmp_path):
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, f"""
            modules:
                - {tmp_path / "mypuzzles.py"}
            puzzles:
                - mypuzzles.move
        """)

        # Should contain the default module and my module
        assert set(tutorial.modules.keys()) == {"default", "mypuzzles"}
        assert {m.__name__ for m in tutorial.modules.values()} == {"default", "mypuzzles"}

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
        with pytest.raises(FileNotFoundError):
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

    def test_solve_puzzle(self, tmp_path):
        tutorial = TestTutorial._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES}, SIMPLE_TUTORIAL)
        tutorial.run()
        puzzle = tutorial.puzzles[0].puzzle

        assert tutorial.solve_puzzle(puzzle) == (False, "Incorrect!")
        assert puzzle.solved == False

        tutorial.file_system.run_command("cp A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle) == (False, "Incorrect!")

        tutorial.file_system.run_command("mv A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle) == (True, "Correct!")
        assert puzzle.solved == True

    def test_solve_puzzle_feedback(self, tmp_path):
        puzzles = """def unsolvable(file_system):
                        return Puzzle(
                            question = f"You can never solve this puzzle.",
                            checker = lambda: "Unsolvable!",
                        )"""
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
        puzzles = """def invalid(file_system):
                        return Puzzle(
                            question = f"This puzzle is invalid",
                            checker = lambda: 100,
                        )"""
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

    # TODO test checker functions with different args.