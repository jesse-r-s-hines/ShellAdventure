import pytest
from shell_adventure.support import Puzzle, call_with_args
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

    def test_pickle_puzzle(self, tmp_path):
        puzzle = Puzzle("Solve this puzzle.", checker = lambda flag: False, score = 1)
        puzzle.solved = True

        data = pickle.dumps(puzzle)
        new_puzzle: Puzzle = pickle.loads(data)

        assert puzzle.question == new_puzzle.question
        assert puzzle.score == new_puzzle.score
        assert puzzle.solved == new_puzzle.solved
        assert puzzle.id == new_puzzle.id
        assert puzzle.checker_args == {"flag"}
        assert new_puzzle._checker == None # Can't pickle lambdas
        assert puzzle._checker != None # Doesn't affect original

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