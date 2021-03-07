"""
Contains miscellaneous support classes and values.
This file is shared between the Docker side code and host,
`shell_adventure/support.py` is a symlink to `shell_adventure_docker/support.py`
"""

from typing import Union, Callable, List
import os, inspect, uuid, time
from multiprocessing.connection import Client
from enum import Enum

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
        self.id = str(uuid.uuid4())

    def __getstate__(self):
        # Can't pickle lambdas, but we don't need it host side.
        return {k:v for k, v in self.__dict__.items() if k != "checker"}

    def _get_checker_params(self):
        """ Returns the paramater list of the checker function. """
        return inspect.getfullargspec(self.checker).args

class PuzzleTree:
    """ A tree node so that puzzles can be unlocked after other puzzles are solved. """
    def __init__(self, generator: str, puzzle: Puzzle = None, dependents: List[Puzzle] = None):
        self.generator = generator
        self.puzzle = puzzle
        self.dependents = dependents if dependents else []

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

class Message(Enum):
    """
    Enum for various messages that can be send between host and docker.
    They will be sent as tuples (enum, *args), in case the message type has parameters.
    """
    
    STOP = 0
    """ Stop the tutorial. Usage: (STOP,) """
    GENERATE = 1
    """ Generate puzzles. Usage: (GENERATE, generator_list) """
    CONNECT_TO_BASH = 2
    """ Tells the container that a bash session has started and to connect to it. Usage: (CONNECT_TO_BASH,) """
    SOLVE = 3
    """ Solve a puzzle. Usage: (SOLVE, puzzle_id) """

def retry_connect(address, authkey, retries = 16, pause = 0.25):
    """ Tries to connect to the given address and authkey, retries a few times if the connection fails. """
    for attempt in range(retries - 1):
        try:
            return Client(address, authkey=authkey)
        except:
            time.sleep(pause)
    return Client(address, authkey=authkey) # Last time just let any errors get raised.