# imports will be part of the package namespace, so you can use shell_adventure_docker.File, etc
from .support import Puzzle
from .file import File
from .permissions import Permissions, change_user
from .random_helper import RandomHelper as _RandomHelper # private import
from .tutorial_docker import TutorialDocker as _TutorialDocker # private import

rand: _RandomHelper = None # TODO rename rand?
"""
The RandomHelper which will be used when creating random files and folders. TutorialDocker will set it when it runs.
Has to be at the package level, and so that File methods can access it.
"""

_tutorial: _TutorialDocker = None
"""
Global that is set to the currently run tutorial, so that File methods can access it.
"""