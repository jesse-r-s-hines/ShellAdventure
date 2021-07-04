"""
This package contains helper code that is shared between the host and the container
"""
from pathlib import Path
PKG_PATH = Path(__path__[0]).resolve() # type: ignore  # mypy issue #1422
