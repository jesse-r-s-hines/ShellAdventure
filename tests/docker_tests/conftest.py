import pytest, os, tempfile
from pathlib import Path

# Defines some fixtures for use in the rest of the tests

@pytest.fixture()
def umask000():
    """
    By default, python won't make any files writable by "other" regardless of mode. This turns that off.
    umask will normally be changed when the tutorial is set up but for testing we need to set it ourselves.

    Note that this fixture should be placed before working_dir or tmp_path, otherwise the tmp directory will
    be created with the old mask instead of the new one.
    """
    prev_mask = os.umask(0o000)
    yield
    os.umask(prev_mask)


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

