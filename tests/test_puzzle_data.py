from typing import Callable
import pytest
from shell_adventure.shared.support import UnrecognizedParamsError
from shell_adventure.api.puzzle import Puzzle
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
        old_puzzle = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda flag: False, score = 2))
        old_puzzle.solved = True

        data = pickle.dumps(old_puzzle)
        new_puzzle: PuzzleData = pickle.loads(data)

        assert old_puzzle.template == new_puzzle.template
        assert old_puzzle.question == "Solve this puzzle."
        assert old_puzzle.score == 2
        assert old_puzzle.solved == True
        assert old_puzzle.id == new_puzzle.id
        assert old_puzzle.checker_args == ["flag"]

        assert isinstance(old_puzzle.checker, Callable) # Doesn't affect original

        # Leaves the lambda as bytes for now, will load it if we use the puzzle
        assert isinstance(new_puzzle.checker, bytes)
        new_puzzle.extract()
        assert isinstance(new_puzzle.checker, Callable)

    def test_pickle_puzzle_already_pickled(self):
        old_puzzle = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda flag: False))

        new_puzzle: PuzzleData = pickle.loads(pickle.dumps(old_puzzle))
        new_puzzle2: PuzzleData = pickle.loads(pickle.dumps(new_puzzle))
        # Pickling twice does not double pickle the lambda
        new_puzzle2.extract()
        assert isinstance(new_puzzle2.checker, Callable)

        # Calling extract twice does nothing
        new_puzzle2.extract()
        assert isinstance(new_puzzle2.checker, Callable)

    def test_pickle_error(self):
        gen = (i for i in range(10))
        old_puzzle = PuzzleData("template", Puzzle("Solve this puzzle.", checker = lambda: gen))

        # generators aren't pickleable, so checker will just be None
        new_puzzle: PuzzleData = pickle.loads(pickle.dumps(old_puzzle))
        assert new_puzzle.checker == None