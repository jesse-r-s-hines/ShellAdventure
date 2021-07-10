import pytest, os, tempfile
from pathlib import Path

# Defines some fixtures for use in the rest of the tests

@pytest.fixture()
def working_dir():
    """
    Creates a temporary directory and sets it as the working directory.
    Returns a Path to the directory.
    Also sets the directory world-writable so "student" user can access the folder.
    """
    with tempfile.TemporaryDirectory(prefix="pytest-working_dir-") as folder:
        os.chdir(folder)
        os.chmod(folder, 0o777) # make it world-writable so student can access it
        yield Path(folder)

