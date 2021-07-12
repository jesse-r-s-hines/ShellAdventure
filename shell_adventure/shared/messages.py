""" Contains the enum used for communicating between the host-side and docker-side parts of the tutorial """
from enum import Enum

conn = ('localhost', 6550)
"""The address that will be used to communicate from the host to the container. """
conn_key = b'shell_adventure.api'
"""The authkey that will be used in communication between the Docker code and the host app. """

class Message(Enum):
    """
    Enum for various messages that can be sent between host and docker.
    They will be sent as tuples (enum, *args), so that the message can have parameters.
    """

    STOP = 'STOP'
    """ Stop the tutorial. Usage: (STOP,) """
    SETUP = 'SETUP'
    """ Send settings and puzzle modules. Generate puzzles. Usage: (SETUP, **kwargs) """
    SOLVE = 'SOLVE'
    """ Solve a puzzle. Usage: (SOLVE, puzzle_id, [flag]) """
    GET_STUDENT_CWD = 'GET_STUDENT_CWD'
    """ Get the path to the students current directory. Usage (GET_STUDENT_CWD,) """
    GET_FILES = 'GET_FILES'
    """ Get files under a folder. Usage (GET_FILES, folder) """
    RESTORE = 'RESTORE'
    """ Restore from a snapshot after a restart. Like SETUP, but we don't regenerate the puzzles. Usage: (RESTORE, **kwargs) """
