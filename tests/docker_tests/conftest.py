import pytest, os

# Defines some fixtures for use in the rest of the tests

@pytest.fixture()
def working_dir(tmp_path):
    """ Creates a temporary directory and sets it as the working directory. Retuns a path to the directory. """
    os.chdir(tmp_path)
    return tmp_path