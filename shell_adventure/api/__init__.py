"""
The shell_adventure.api package contains the classes and methods needed to make puzzle templates and autograders
"""

from __future__ import annotations
from .puzzle import Puzzle
from .file import File
from .permissions import Permissions, change_user
from .random_helper import RandomHelper, RandomHelperException

from pathlib import Path as _Path # "private" import

PKG_PATH = _Path(__path__[0]).resolve() # type: ignore  # mypy issue #1422

# Unfortunately we need some package level variables to allow File methods to access
# the RandomHelper and student home. They will be set when the tutorial is created.
_home: File = None
""" Global that is set to the home of the student. """

_rand: RandomHelper = None
"""
Global that is set to the `RandomHelper` of the tutorial, so that `rand()` and `File` methods can access it.
"""

# After restart and pickling the lambdas we don't restore the RandomHelper state so we don't want you to be able to
# call it in autograder functions. So we make rand a function so that it doesn't get captured directly, that way we can
# set tutorial.rand to None and trying to use rand() will fail.
# TutorialDocker will set _rand when it runs.
def rand() -> RandomHelper:
    """
    Returns the `RandomHelper` which should be used when creating random files and folders. 
    """
    if not _rand:
        raise RandomHelperException("You can only use randomization in Puzzle templates, not autograders")
    return _rand

__all__ = [
    "file",
    "permissions",
    "random_helper",
    "puzzle",
    "Puzzle",
    "File",
    "Permissions",
    "change_user",
    "rand",
]