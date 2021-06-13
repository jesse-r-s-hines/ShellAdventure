"""
Contains miscellaneous support classes and values.
This file is shared between the Docker side code and host. It will be copied into the container
as part of the shell_adventure package.
"""

from __future__ import annotations
from typing import Union, Callable, List, Dict, Any, Set, ClassVar, cast
import os, time, uuid, inspect, dill
from pathlib import Path
from enum import Enum

PathLike = Union[str, os.PathLike]
"""Type for a string representing a path or a PathLike object."""

conn_addr_to_container = ('localhost', 6000)
"""The address that will be used to communicate from the host to the container. """
conn_addr_from_container = ('localhost', 6001)
"""The address that will be used to communicate from the container to the host. """
conn_key = b'shell_adventure'
"""The authkey that will be used in communication between the Docker code and the host app. """

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

    checker_args: Set[str]
    """ A set of the args of this puzzles checker function. """

    allowed_checker_args: ClassVar[Set[str]] = {"cwd", "flag"}
    """ A set of the checker args that are recognized. """

    def __init__(self, question: str, checker: AutoGrader, score = 1):
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

        self.question = question
        self.score = score
        self.checker = checker # type: ignore # MyPy fusses about "Cannot assign to a method"
        self.solved = False
        self.id = str(uuid.uuid4())
        self.checker_args = set(inspect.getfullargspec(self.checker).args)
        if not self.checker_args.issubset(Puzzle.allowed_checker_args): # TODO use custom exception
            raise Exception(f'Unrecognized parameters ({", ".join(self.checker_args - Puzzle.allowed_checker_args)}), ' +
                            f'checker functions can only have some combination of parameters ({", ".join(Puzzle.allowed_checker_args)}).')

    def __getstate__(self):
        """
        We have to use dill to pickle lambdas. We won't unpickle it on the host, since we don't need to call it and there may
        be modules in the container that aren't on the host causing unpickle to fail. We do need to be able to send the pickled
        lambda back to the container after an undo. If the checker fails to pickle, it will be left as None
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
        We don't want to unpickle the checker on the host, but we need to be able to send it back to the container after a undo.
        Calling extract() will unpickle the checker after we have received a puzzle from the host.
        """
        if isinstance(self.checker, bytes):
            self.checker = dill.loads(self.checker)

PuzzleGenerator = Callable[..., Puzzle]
AutoGrader = Callable[..., Union[str,bool]]


# We aren't using this class currently
# class CommandOutput: # TODO
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
    
    STOP = 'STOP'
    """ Stop the tutorial. Usage: (STOP,) """
    SETUP = 'SETUP'
    """ Send settings and puzzle modules. Generate puzzles. Usage: (GENERATE, kwargs) """
    SOLVE = 'SOLVE'
    """ Solve a puzzle. Usage: (SOLVE, puzzle_id, [flag]) """
    GET_STUDENT_CWD = 'GET_STUDENT_CWD'
    """ Get the path to the students current directory. Usage (GET_CWD,) """
    GET_FILES = 'GET_FILES'
    """ Get files under a folder. Usage (GET_FILES, folder) """
    RESTORE = 'RESTORE'
    """ Restore from a snapshot after an UNDO. Like SETUP, but we don't regenerate the puzzles. Usage: (RESTORE, kwargs) """
    MAKE_COMMIT = 'MAKE_COMMIT'
    """ Make a Docker commit of the container so we can undo a command. """

class ScriptType(Enum):
    """ Enum for sending setup_scripts. """
    BASH = 0
    PYTHON = 1

def call_with_args(func: Callable[..., Any], args: Dict[str, Any]):
    """
    Takes a function and a map of args to their names. Any values in args that have the same name as a parameter of func
    will be passed to func. Ignores missing args, and will throw an error func has parameters that aren't in args.
    Returns the return result of func.
    """
    func_params = set(inspect.getfullargspec(func).args)
    known_args = set(args.keys())

    # Make sure there are no unrecognized parameters
    if not func_params.issubset(known_args): # TODO use custom exception
        raise Exception(f'Unrecognized parameters ({", ".join(func_params - known_args)}), expected some combination of ({", ".join(known_args)}).')

    # Only pass the args that the checker function has
    args_to_pass = {param: args[param] for param in func_params}
    return func(**args_to_pass)

def retry(func: Callable[[], Any], tries = 16, delay = 0.25):
    """
    Retries the given function until it succeeds without an error.
    tries is the maximum number of tries. If <= 0, infinite tries.
    delay is delay betwen tries
    """
    for attempt in range(tries - 1):
        try:
            return func()
        except:
            time.sleep(delay)
    return func() # Last time just let the errors get raised.