from .puzzle import Puzzle
from .file import File
from .permissions import Permissions, change_user
from .random_helper import RandomHelper
from .tutorial_docker import TutorialDocker
from pathlib import Path

PKG_PATH = Path(__path__[0]) # type: ignore  # mypy issue #1422

rand: RandomHelper = None # TODO rename rand?
"""
The RandomHelper which will be used when creating random files and folders. TutorialDocker will set it when it runs.
Has to be at the package level, and so that File methods can access it.
"""

_tutorial: TutorialDocker = None
"""
Global that is set to the currently run tutorial, so that File methods can access it.
"""

__all__ = [
    "file",
    "permissions",
    "Puzzle",
    "File",
    "Permissions",
    "change_user",
    "rand",
]