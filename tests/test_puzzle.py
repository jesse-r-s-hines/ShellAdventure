import pytest, re
from shell_adventure.shared.support import UnrecognizedParamsError
from shell_adventure.shared.puzzle import Puzzle

class TestPuzzle:
    def test_create_puzzle(self):
        puzzle = Puzzle("Solve this puzzle.", checker = lambda cwd, flag: False)

    def test_create_puzzle_invalid_args(self):
        with pytest.raises(UnrecognizedParamsError, match = re.escape("Unrecognized param(s) 'blah'")):
            puzzle = Puzzle("Solve this puzzle.", checker = lambda blah: False)

    def test_create_puzzle_invalid_types(self):
        with pytest.raises(TypeError, match = "Puzzle.checker"):
            puzzle = Puzzle(
                question = "Hey",
                checker = "Not a lambda",
            )

        with pytest.raises(TypeError, match = "Puzzle.question"):
            puzzle = Puzzle(
                question = 1,
                checker = lambda: False,
            )
