""" Package containing code that is shared between the container and the host. """
from pathlib import Path
PKG_PATH = Path(__path__[0]) # type: ignore  # mypy issue #1422
