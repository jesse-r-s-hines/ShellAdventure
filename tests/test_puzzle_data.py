from typing import Callable, Type
import pytest
from shell_adventure.shared.support import UnrecognizedParamsError
from shell_adventure.shared.puzzle import Puzzle
from shell_adventure.shared.puzzle_data import PuzzleData
import pickle

class TestPuzzleData:
    def test_create_puzzle_data(self):
        puzzle = PuzzleData("puzzles.puzz", Puzzle("Solve this puzzle.", checker = lambda cwd, flag: False))

        assert puzzle.id.startswith("puzzles.puzz-")

        assert puzzle.template == "puzzles.puzz"
        assert puzzle.question == "Solve this puzzle."
        assert puzzle.solved == False
        assert puzzle.checker_args == ["cwd", "flag"]

    def test_pickle_puzzle_data(self):
        original_puzzle = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda flag: False, score = 2))
        original_puzzle.solved = True

        packed_puzzle = original_puzzle.checker_dilled()
        assert isinstance(packed_puzzle.checker, bytes)
        assert packed_puzzle is not original_puzzle # Returns a new puzzle
        assert isinstance(original_puzzle.checker, Callable) # Doesn't affect original

        new_puzzle: PuzzleData = pickle.loads(pickle.dumps(packed_puzzle))
        # Leaves the lambda as bytes for now, will load it if we use the puzzle
        assert isinstance(new_puzzle.checker, bytes)

        unpacked_puzzle = new_puzzle.checker_undilled()
        assert isinstance(unpacked_puzzle.checker, Callable)
        assert unpacked_puzzle is not new_puzzle # Returns a new puzzle

        assert unpacked_puzzle.template == "template"
        assert unpacked_puzzle.question == "Solve this puzzle."
        assert unpacked_puzzle.score == 2
        assert unpacked_puzzle.solved == True
        assert unpacked_puzzle.id == new_puzzle.id
        assert unpacked_puzzle.checker_args == ["flag"]

    def test_pickle_puzzle_already_pickled(self):
        orig = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda flag: False))

        puzzle1 = orig.checker_dilled()
        puzzle2 = puzzle1.checker_dilled() # Calling packed twice doesn't do anything but copy
        assert isinstance(puzzle1.checker, bytes)
        assert puzzle1.checker == puzzle2.checker
        assert puzzle1 is not puzzle2

        puzzle3 = puzzle2.checker_undilled()
        puzzle4 = puzzle3.checker_undilled() # Calling unpacked twice doesn't do anything but copy
        assert isinstance(puzzle4.checker, Callable)
        assert puzzle3 is not puzzle4

    def test_pickle_error(self):
        puzzle = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda: True))
        # Pickle throws attribute error instead of PickleError for some reason.
        # See https://bugs.python.org/issue29187
        with pytest.raises(AttributeError, match = "pickle .*lambda"):
            data = pickle.dumps(puzzle)

        # But packing first should work
        data = pickle.dumps(puzzle.checker_dilled())
        puzzle = pickle.loads(data).checker_undilled()

        # Generators can't be dilled
        gen = (i for i in range(10))
        puzzle = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda: gen))
        with pytest.raises(TypeError, match = "pickle .*generator"): # And dill throws TypeError instead of PickleError. That is useless.
            puzzle.checker_dilled()

    def test_checker_stripped(self):
        puzzle = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda: True))
        new = puzzle.checker_stripped()

        assert new.checker == None
        assert puzzle is not new
