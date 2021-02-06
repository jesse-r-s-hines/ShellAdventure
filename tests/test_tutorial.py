import pytest
from pytest import mark
from shell_adventure.tutorial import *

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
    def test_creation(self, tmp_path):
        puzzles = tmp_path / "mypuzzles.py"
        puzzles.write_text(SIMPLE_PUZZLES)

        config = tmp_path / "tutorial.yaml"
        config.write_text(f"""
            modules:
                - {puzzles}
            puzzles:
                - mypuzzles.move
        """)

        tutorial = Tutorial(config)
        assert tutorial.config_file == config

        # Should contain the default module and my module
        assert set(tutorial.modules.keys()) == {"default", "mypuzzles"}
        assert {m.__name__ for m in tutorial.modules.values()} == {"default", "mypuzzles"}

        assert "mypuzzles.move" in tutorial.generators
        assert tutorial.puzzles[0].generator == "mypuzzles.move" # Not generated yet
        assert tutorial.puzzles[0].puzzle == None # Not generated yet

    def test_relative_path_creation(self, tmp_path):
        (tmp_path / "mypuzzles.py").write_text(SIMPLE_PUZZLES)

        config = tmp_path / "tutorial.yaml"
        config.write_text(SIMPLE_TUTORIAL)

        tutorial = Tutorial(f"{config}") # Strings should also work for path
        assert "mypuzzles.move" in tutorial.generators

    def test_multiple_modules(self, tmp_path):
        (tmp_path / "mypuzzles1.py").write_text(SIMPLE_PUZZLES)
        (tmp_path / "mypuzzles2.py").write_text(SIMPLE_PUZZLES)

        config = tmp_path / "tutorial.yaml"
        config.write_text(f"""
            modules:
                - mypuzzles1.py
                - mypuzzles2.py
            puzzles:
                - mypuzzles1.move
        """)

        tutorial = Tutorial(config)
        assert "mypuzzles1.move" in tutorial.generators
        assert "mypuzzles2.move" in tutorial.generators

    def test_missing_module(self, tmp_path):
        config = tmp_path / "tutorial.yaml"
        config.write_text(SIMPLE_TUTORIAL)

        with pytest.raises(FileNotFoundError):
            tutorial = Tutorial(config)

    def test_missing_puzzle(self, tmp_path):
        config = tmp_path / "tutorial.yaml"
        config.write_text(f"""
            puzzles:
                - default.not_a_puzzle_name
        """)

        with pytest.raises(AssertionError, match="Unknown puzzle generator default.not_a_puzzle_name"):
            tutorial = Tutorial(config)


    def test_solve_puzzle(self, tmp_path):
        (tmp_path / "mypuzzles.py").write_text(SIMPLE_PUZZLES)
        config = tmp_path / "tutorial.yaml"
        config.write_text(f"""
            modules:
                - mypuzzles.py
            puzzles:
                - mypuzzles.move
        """)
        tutorial = Tutorial(config)
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
        (tmp_path / "mypuzzles.py").write_text("""
def unsolvable(file_system):
    return Puzzle(
        question = f"You can never solve this puzzle.",
        checker = lambda: "Unsolvable!",
    )
        """)

        config = tmp_path / "tutorial.yaml"
        config.write_text(f"""
            modules:
                - mypuzzles.py
            puzzles:
                - mypuzzles.unsolvable
        """)
        tutorial = Tutorial(config)
        tutorial.run()
        puzzle = tutorial.puzzles[0].puzzle

        assert tutorial.solve_puzzle(puzzle) == (False, "Unsolvable!")
        assert puzzle.solved == False

    def test_solve_puzzle_error(self, tmp_path):
        (tmp_path / "mypuzzles.py").write_text("""
def invalid(file_system):
    return Puzzle(
        question = f"This puzzle is invalid",
        checker = lambda: 100,
    )
        """)

        config = tmp_path / "tutorial.yaml"
        config.write_text(f"""
            modules:
                - mypuzzles.py
            puzzles:
                - mypuzzles.invalid
        """)
        tutorial = Tutorial(config)
        tutorial.run()
        puzzle = tutorial.puzzles[0].puzzle

        with pytest.raises(Exception, match="bool or str expected"):
            tutorial.solve_puzzle(puzzle)

    # TODO test checker functions with different args.