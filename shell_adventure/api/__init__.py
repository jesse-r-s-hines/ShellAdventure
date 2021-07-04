"""
The shell_adventure.api package contains the classes and methods needed to make puzzle templates and autograders
"""

from __future__ import annotations
from .puzzle import Puzzle
from .file import File
from .permissions import Permissions, change_user

# "private" imports
from shell_adventure.docker_side import random_helper as _random_helper
from shell_adventure.docker_side import tutorial_docker as _tutorial_docker
from pathlib import Path as _Path

PKG_PATH = _Path(__path__[0]).resolve() # type: ignore  # mypy issue #1422

_tutorial: _tutorial_docker.TutorialDocker = None
"""
Global that is set to the currently run tutorial, so that rand() and File methods can access it.
"""

# After restart and pickling the lambdas we don't restore the RandomHelper state so we don't want you to be able to
# call it in autograder functions. So we make rand a function so that it doesn't get captured directly, that way we can
# set tutorial.rand to None and trying to use rand() will fail.
def rand() -> _random_helper.RandomHelper:
    """
    The RandomHelper which will be used when creating random files and folders. TutorialDocker will set it when it runs.
    Has to be at the package level, and so that File methods can access it.
    """
    if not _tutorial or not _tutorial.rand:
        raise _random_helper.RandomHelperException("You can only use randomization in Puzzle templates, not autograders")
    return _tutorial.rand

__all__ = [
    "file",
    "permissions",
    "Puzzle",
    "File",
    "Permissions",
    "change_user",
    "rand",
]