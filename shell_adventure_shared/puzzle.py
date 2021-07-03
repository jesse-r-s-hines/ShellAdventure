"""
The Puzzle class
"""

from __future__ import annotations
from typing import Union, Callable, List, ClassVar
import uuid, inspect, dill
from shell_adventure_shared.support import extra_func_params, UnrecognizedParamsError, sentence_list

class Puzzle:
    """ Represents a single puzzle in the tutorial. """

    question: str

    score: int

    checker: Union[AutoGrader, bytes]
    """
    The function that will be used to autograde the puzzle.
    When a Puzzle is sent to the host, checker will be left as pickled version of the checker.
    We don't want to unpickle the checker on the host since there may be modules on the client that aren't on the host.
    """

    solved: bool
    """ Whether the puzzle is solved yet """

    id: str
    """ A unique identifier for the puzzle. """

    allowed_checker_args: ClassVar[List[str]] = ["cwd", "flag"]
    """ A set of the checker args that are recognized. """

    def __init__(self, question: str, checker: AutoGrader, score: int = 1):
        """
        Construct a Puzzle object.

        Parameters:

        question:
            The question to be asked.
        checker:
            The function that will grade whether the puzzle was completed correctly or not.
            The function can take the following parameters. All parameters are optional, and order does not matter,
            but must have the same name as listed here.
            flag: str
                If the flag parameter is present, an input dialog will be shown to the student when sumbitting a puzzle,
                and their input will be passed to this parameter.
            cwd: File
                The path to the students current directory

            The function will return a string or a boolean. If it returns True, the puzzle is solved. If it returns
            False or a string, the puzzle was not solved, and the string will be shown as feedback to the student.
        score:
            The score given on success. Defaults to 1. 
        """
        if not isinstance(question, str): raise TypeError("Puzzle.question should be a string.")
        if not callable(checker): raise TypeError("Puzzle.checker should be a Callable.")
        if not isinstance(score, int): raise TypeError("Puzzle.score should be an int.")

        self.question = question
        self.score = score
        self.checker = checker # type: ignore # MyPy fusses about "Cannot assign to a method"
        self.solved = False
        self.id = str(uuid.uuid4())

        self._checker_args = inspect.getfullargspec(self.checker).args # args of the checker function.
        extra_params = extra_func_params(self.checker, Puzzle.allowed_checker_args)
        if extra_params:
            raise UnrecognizedParamsError(
                f'Unrecognized param(s) {sentence_list(extra_params, quote = True)} in checker function.' +
                f' Expected {sentence_list(Puzzle.allowed_checker_args, last_sep = " and/or ", quote = True)}.',
                extra_params = extra_params
            )

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
            except: # If pickling fails, checker is None
                data["checker"] = None
        return data

    def extract(self): # TODO I need to find a cleaner way of doing this
        """
        We don't want to unpickle the checker on the host, but we need to be able to send it back to the container after a restart.
        Calling extract() will unpickle the checker after we have received a puzzle from the host.
        """
        if isinstance(self.checker, bytes):
            self.checker = dill.loads(self.checker)

PuzzleGenerator = Callable[..., Puzzle]
AutoGrader = Callable[..., Union[str,bool]]
