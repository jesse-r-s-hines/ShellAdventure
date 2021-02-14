from typing import *
import pytest
from pytest import mark
from shell_adventure.docker_scripts.file import File
import os, stat, pathlib

class TestFile:
    def test_basic(self, tmp_path):
        os.chdir(tmp_path)

        dir = File("A")
        file = dir / "a.txt"
        assert isinstance(file, File)
        
        file = File(tmp_path, "b.txt")
        assert file.exists() == False
        file.write_text("STUFF")
        assert file.read_text() == "STUFF"

    def test_path(self, tmp_path):
        os.chdir(tmp_path)

        file = File("A/B.txt")
        assert file.path.startswith("/")
        assert file.path.endswith("A/B.txt")

    def test_touch(self, tmp_path):
        os.chdir(tmp_path)
        # By default, python won't make any files writable by "other". This turns that off. This will be called in docker container
        # TODO if we move these tests into the container I should remove this and make sure the container has it set right.
        os.umask(0o000)

        file = File("A/B.txt")
        assert not file.parent.exists()
        assert not file.exists()

        with pytest.raises(FileNotFoundError):
            file.touch()
        file.touch(mode=0o644, recursive=True)

        assert file.exists()
        assert file.parent.exists()
        # TODO use permissions object once I've added that
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o644
        assert stat.S_IMODE(os.stat("A").st_mode) == 0o755

        File("A/C.txt").touch(mode=0o666, recursive=True)
        assert stat.S_IMODE(os.stat("A/C.txt").st_mode) == 0o666
        assert stat.S_IMODE(os.stat("A").st_mode) == 0o755 # Does not change permissions of existing folders.

        file = File("A/D.txt")
        file.touch()
        assert file.exists()


    def test_children(self, tmp_path):
        os.chdir(tmp_path)

        dir = File("dir")
        dir.mkdir()
        for name in ["A.txt", "B.txt", "C.txt"]:
            (dir / name).touch()

        with pytest.raises(NotADirectoryError):
            (dir / "A.txt").children()
        
        assert isinstance(dir.children(), list)
        assert isinstance(dir.children()[0], File)

        names = {f.name for f in dir.children()}
        assert names == {"A.txt", "B.txt", "C.txt"}