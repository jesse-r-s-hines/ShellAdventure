# Logically this should be in the api module. But I can't import the api module from shared since that will cause circular dependencies issues and
# since shared is used host-side and docker-side, cause api with Linux only modules to imported host-side.
from __future__ import annotations
from typing import Union, Callable, List, ClassVar
from shell_adventure.shared.support import extra_func_params, UnrecognizedParamsError, sentence_list

class Puzzle:
    """ Represents a single puzzle in the tutorial. """

    question: str

    score: int

    checker: AutoGrader
    """
    The function that will be used to autograde the puzzle.
    """

    _allowed_checker_args: ClassVar[List[str]] = ["cwd", "flag"]
    """ A set of the checker args that are recognized. """

    def __init__(self, question: str, checker: AutoGrader, score: int = 1):
        """
        Construct a `Puzzle` object.

        Parameters:

        question:
            The question to be asked.
        checker:
            The function that will grade whether the puzzle was completed correctly or not.
            The checker function can take the following parameters. All parameters are optional, and order does not matter,
            but the parameters must have the same name as listed here:
                flag: str
                    If the flag parameter is present, an input dialog will be shown to the student when sumbitting a puzzle,
                    and their input will be passed to this parameter.
                cwd: File
                    The path to the students current directory

            The checker function should return a string or a boolean. If it returns True, the puzzle is solved. If it returns
            False or a string, the puzzle was not solved. Returning a string will show the string as feedback to the student.
        score:
            The score given on success. Defaults to 1.
        """
        if not isinstance(question, str): raise TypeError("Puzzle.question should be a string.")
        if not callable(checker): raise TypeError("Puzzle.checker should be a Callable.")
        if not isinstance(score, int): raise TypeError("Puzzle.score should be an int.")

        self.question = question
        self.score = score
        self.checker = checker # type: ignore # MyPy fusses about "Cannot assign to a method"

        extra_params = extra_func_params(self.checker, Puzzle._allowed_checker_args)
        if extra_params:
            raise UnrecognizedParamsError(
                f'Unrecognized param(s) {sentence_list(extra_params, quote = True)} in checker function.' +
                f' Expected {sentence_list(Puzzle._allowed_checker_args, last_sep = " and/or ", quote = True)}.',
                extra_params = extra_params
            )

PuzzleTemplate = Callable[..., Puzzle]
AutoGrader = Callable[..., Union[str,bool]]
