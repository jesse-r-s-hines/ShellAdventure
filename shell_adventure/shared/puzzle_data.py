
from __future__ import annotations
from typing import Union, List
import uuid, inspect, dill
from shell_adventure.api.puzzle import Puzzle, PuzzleTemplate, AutoGrader

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

    def __getstate__(self):
        """
        We have to use dill to pickle lambdas. We won't unpickle it on the host, since we don't need to call it and there may
        be modules in the container that aren't on the host causing unpickle to fail. We do need to be able to send the pickled
        lambda back to the container after a restart. If the checker fails to pickle, it will be left as None
        """
        data = self.__dict__.copy()
        if not isinstance(self.checker, bytes):
            try:
                data["checker"] = dill.dumps(self.checker, recurse = True)
            except: # If pickling fails, checker is set to None
                data["checker"] = None
        return data

    def extract(self):
        """
        We don't want to unpickle the checker on the host, but we need to be able to send it back to the container after a restart.
        Calling extract() will unpickle the checker after we have received a puzzle from the host.
        """
        if isinstance(self.checker, bytes):
            self.checker = dill.loads(self.checker)
