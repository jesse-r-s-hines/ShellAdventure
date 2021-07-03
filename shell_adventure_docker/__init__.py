from shell_adventure_shared.puzzle import Puzzle
from .file import File
from .permissions import Permissions, change_user
from .random_helper import RandomHelper, RandomHelperException
from .tutorial_docker import TutorialDocker
from pathlib import Path

PKG_PATH = Path(__path__[0]).resolve() # type: ignore  # mypy issue #1422

_tutorial: TutorialDocker = None
"""
Global that is set to the currently run tutorial, so that File methods can access it.
"""

# After restart and pickling the lambdas we don't restore the RandomHelper state so we don't want you to be able to
# call it in autograder functions. So we make rand a function so that it doesn't get captured directly, that way we can
# set tutorial.rand to None and trying to use rand() will fail.
def rand() -> RandomHelper:
    """
    The RandomHelper which will be used when creating random files and folders. TutorialDocker will set it when it runs.
    Has to be at the package level, and so that File methods can access it.
    """
    if not _tutorial or not _tutorial.rand:
        raise RandomHelperException("You can only use randomization in Puzzle generators, not auto-graders")
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