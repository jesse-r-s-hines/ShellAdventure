from typing import Callable
import pytest
from shell_adventure.support import AutoGrader, Puzzle, call_with_args
import pickle

class TestSupport:
    def test_create_puzzle(self):
        puzzle = Puzzle("Solve this puzzle.", checker = lambda cwd, flag: False)

        assert puzzle.solved == False
        assert puzzle.checker_args == {"cwd", "flag"}

    def test_create_puzzle_invalid_args(self):
        with pytest.raises(Exception, match=r"Unrecognized parameters \(blah\)"):
            puzzle = Puzzle("Solve this puzzle.", checker = lambda blah: False)

    def test_solve_puzzle(self):
        puzzle = Puzzle("Solve this puzzle.", checker = lambda: "Feedback!")
        assert puzzle.solve({}) == (False, "Feedback!")

        puzzle = Puzzle("Solve this puzzle.", checker = lambda flag: flag == "a")
        assert puzzle.solve({"flag": "a"}) == (True, "Correct!")\
        # Calling twice on a puzzle resets the solved state.
        assert puzzle.solve({"flag": "b"}) == (False, "Incorrect!")


    def test_solve_puzzle_bad_return(self):
        puzzle = Puzzle(
            question = f"This puzzle is invalid",
            checker = lambda: 100,
        )
        with pytest.raises(Exception, match="bool or str expected"):
            puzzle.solve({})

    def test_pickle_puzzle(self):
        old_puzzle = Puzzle("Solve this puzzle.", checker = lambda flag: False, score = 2)
        old_puzzle.solved = True

        data = pickle.dumps(old_puzzle)
        new_puzzle: Puzzle = pickle.loads(data)

        assert old_puzzle.question == new_puzzle.question
        assert old_puzzle.score == new_puzzle.score
        assert old_puzzle.solved == new_puzzle.solved
        assert old_puzzle.id == new_puzzle.id
        assert old_puzzle.checker_args == {"flag"}

        assert isinstance(old_puzzle._checker, Callable) # Doesn't affect original

        # Leaves the lambda as bytes for now, will load it if we use the puzzle
        assert isinstance(new_puzzle._checker, bytes)
        new_puzzle.extract()
        assert isinstance(new_puzzle._checker, Callable)

        assert new_puzzle.solve({"flag": "a"}) == (False, "Incorrect!")

    def test_pickle_puzzle_already_pickled(self):
        old_puzzle = Puzzle("Solve this puzzle.", checker = lambda flag: False)

        new_puzzle: Puzzle = pickle.loads(pickle.dumps(old_puzzle))
        new_puzzle2: Puzzle = pickle.loads(pickle.dumps(new_puzzle))
        # Pickling twice does not double pickle the lambda
        new_puzzle2.extract()
        assert isinstance(new_puzzle2._checker, Callable)

        # Calling extract twice does nothing
        new_puzzle2.extract()
        assert isinstance(new_puzzle2._checker, Callable)

    def test_call_with_args(self):
        args = {"a": 1, "b": 2, "c": 3}

        func = lambda a, b, c: (a, b, c)
        assert call_with_args(func, args) == (1, 2, 3)

        func = lambda a, b: (a, b)
        assert call_with_args(func, args) == (1, 2)

        func = lambda c: c
        assert call_with_args(func, args) == 3

        func = lambda: True
        assert call_with_args(func, args) == True

    def test_call_with_args_error(self):
        args = {"a": 1, "b": 2, }

        func = lambda c: True
        with pytest.raises(Exception, match = r'Unrecognized parameters \(c\), expected some combination of \([ab], [ab]\)\.'): # TODO this should be a custom error
            call_with_args(func, args)