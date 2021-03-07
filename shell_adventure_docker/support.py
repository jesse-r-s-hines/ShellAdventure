"""
Contains miscellaneous support classes and values.
This file is shared between the Docker side code and host,
`shell_adventure/support.py` is a symlink to `shell_adventure_docker/support.py`
"""

from typing import Union, Callable
import os, inspect, uuid

PathLike = Union[str, os.PathLike]
"""Type for a string representing a path or a PathLike object."""

conn_addr = ('localhost', 6000)
"""The address that will be used to communicate between the Docker code and the host app. """
conn_key = b'shell_adventure'
"""The authkey that will be used in communication between the Docker code and the host app. """

class Puzzle:
    """ Represents a single puzzle in the tutorial. """

    question: str
    """ The question to be asked. """

    score: int
    """ The score given on success. Defaults to 1. """

    checker: Callable[..., Union[str,bool]]
    """
    The function that will grade whether the puzzle was completed correctly or not.
    The function can take the following parameters. All parameters are optional, and order does not matter,
    but must have the same name as listed here.

    output: Dict[str, CommandOutput]
        A dict of all commands entered to their outputs, in the order they were entered.
    flag: str
        If the flag parameter is present, an input dialog will be shown to the student when sumbitting a puzzle,
        and their input will be passed to this parameter.
    file_system: FileSystem
        A frozen FileSystem object. Most methods that modify the file system will be disabled.
    """

    solved: bool
    """ Whether the puzzle is solved yet """

    id: str
    """ A unique identifier for the puzzle. """

    def __init__(self, question: str, checker: Callable[..., Union[str,bool]] , score = 1):
        self.question = question
        self.score = score
        self.checker = checker # type: ignore # MyPy fusses about "Cannot assign to a method"
        self.solved = False
        self.id = uuid.uuid4()

    def _get_checker_params(self):
        """ Returns the paramater list of the checker function. """
        return inspect.getfullargspec(self.checker).args

# We aren't using this class currently
# class CommandOutput:
#     """ Represents the output of a command. """

#     exit_code: int
#     """ The exit code that the command returned """

#     output: str
#     """ The printed output of the command """

#     # error: str
#     # """ Output to std error """

#     def __init__(self, exit_code: int, output: str):
#         self.exit_code = exit_code
#         self.output = output

#     def __iter__(self):
#         """ Make it iterable so we can unpack it. """
#         return iter((self.exit_code, self.output))