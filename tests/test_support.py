import pytest
from shell_adventure.support import Puzzle
import pickle

class TestSupport:
    def test_pickle_puzzle(self, tmp_path):
        puzzle = Puzzle("Solve this puzzle.", checker = lambda: False, score = 1)
        puzzle.solved = True

        data = pickle.dumps(puzzle)
        new_puzzle: Puzzle = pickle.loads(data)

        assert puzzle.question == new_puzzle.question
        assert puzzle.score == new_puzzle.score
        assert puzzle.solved == new_puzzle.solved
        assert puzzle.id == new_puzzle.id
        assert new_puzzle.checker == None # Can't pickle lambdas
        assert puzzle.checker != None # Doesn't affect original


