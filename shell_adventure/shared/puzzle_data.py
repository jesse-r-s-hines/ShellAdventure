
from __future__ import annotations
from typing import Union, List
import uuid, inspect, dill, copy
from shell_adventure.shared.puzzle import Puzzle, PuzzleTemplate, AutoGrader

class PuzzleData:
    """
    This represents a puzzle template with all associated metadata. Is is created from a Puzzle object, which
    is what the user's template functions will return, but adds some additional data.
    """

    question: str
    score: int

    checker: Union[AutoGrader, bytes]
    """
    The function that will be used to autograde the puzzle.
    When a Puzzle is sent to the host, checker will be left as pickled version of the checker.
    We don't want to unpickle the checker on the host since there may be modules on the client that aren't on the host.
    """

    checker_args: List[str]
    """ The arguments of the checker function. """

    id: str
    """ A unique identifier for the puzzle. """

    template: str
    """ The name of the PuzzleTemplate used to generate this puzzle. """

    solved: bool
    """ Whether the puzzle is solved yet """

    def __init__(self, template: str, puzzle: Puzzle):
        """ Construct a PuzzleData object from a Puzzle and a template name """
        self.question = puzzle.question
        self.score = puzzle.score
        self.checker = puzzle.checker
        self.checker_args = inspect.getfullargspec(self.checker).args

        self.id = f"{template}-{uuid.uuid4()}"
        self.template = template
        self.solved = False

    def checker_dilled(self):
        """
        We have to use dill to pickle lambdas so we can restore the checker functions after a restart. We won't unpickle it on
        the host, since we don't need to call it and there may be modules in the container that aren't on the host causing
        unpickle to fail. We do need to be able to send the pickled lambda back to the container after a restart.

        Before sending a PuzzleData to the host, convert it with checker_dilled(). Then after a restart when the host sends the
        container the PuzzleData's, use checker_undilled() to restore the checkers.

        This function returns a new PuzzleData with checker function serialized with dill. Will throw if the checker is
        unpickleable. Just returns a new PuzzleData if the checker is already pickled
        """
        new = copy.copy(self)
        if not isinstance(self.checker, bytes):
            new.checker = dill.dumps(self.checker, recurse = True)
        return new

    def checker_undilled(self):
        """
        Returns a new PuzzleData with the checker function unpickled. Throws if the checker function can't be unpickled.
        Just returns a new PuzzleData if the checker is already unpickled.
        """
        new = copy.copy(self)
        if isinstance(self.checker, bytes):
            new.checker = dill.loads(self.checker)
        return new

    def checker_stripped(self):
        """
        Returns a new PuzzleData with the checker set to None.
        """
        new = copy.copy(self)
        new.checker = None
        return new