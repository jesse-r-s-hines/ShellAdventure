import pytest
from shell_adventure_docker.file import File
from shell_adventure_docker.utilities import change_user
import os, stat

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

    def test_create(self, tmp_path):
        os.chdir(tmp_path)
        # By default, python won't make any files writable by "other". This turns that off. This will be called in docker container
        # TODO if we move these tests into the container I should remove this and make sure the container has it set right.
        os.umask(0o000)

        file = File("A/B.txt")
        assert not file.parent.exists()
        assert not file.exists()

        with pytest.raises(FileNotFoundError):
            file.create(recursive=False)
        file.create(mode=0o644, recursive=True)

        assert file.exists()
        assert file.parent.exists()
        # TODO use permissions object once I've added that
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o644
        assert stat.S_IMODE(os.stat("A").st_mode) == 0o755

        File("A/C.txt").create(mode=0o666, recursive=True)
        assert stat.S_IMODE(os.stat("A/C.txt").st_mode) == 0o666
        assert stat.S_IMODE(os.stat("A").st_mode) == 0o755 # Does not change permissions of existing folders.

        file = File("A/D.txt")
        file.create()
        assert file.exists()

    def test_children(self, tmp_path):
        os.chdir(tmp_path)

        dir = File("dir")
        for name in ["A.txt", "B.txt", "C.txt"]:
            (dir / name).create()

        with pytest.raises(NotADirectoryError):
            (dir / "A.txt").children()
        
        assert isinstance(dir.children(), list)
        assert isinstance(dir.children()[0], File)

        names = {f.name for f in dir.children()}
        assert names == {"A.txt", "B.txt", "C.txt"}

    def test_chmod(self, tmp_path):
        os.chdir(tmp_path)

        file = File("a.txt")
        file.create()

        # TODO use permissions object once I've added that
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o666

        file.chmod(0o000)
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o000

        file.chmod(0o777)
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o777

        file.chmod("o-wx,g-wx")
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o744

        file.chmod("g+w,u=x")
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o164

    def test_chmod_errors(self, tmp_path):
        os.chdir(tmp_path)

        file = File("a.txt")

        with pytest.raises(FileNotFoundError):
            file.chmod(0o000)
        with pytest.raises(FileNotFoundError):
            file.chmod("u+g")
        file.create()

        with pytest.raises(Exception, match="Invalid mode"):
            file.chmod("not-a-chmod-string")

    def test_chown(self, tmp_path):
        os.chdir(tmp_path)

        file = File("a.txt")
        file.create()
        assert (file.owner(), file.group()) == ("root", "root")

        file.chown("student")
        assert (file.owner(), file.group()) == ("student", "root")

        file.chown(None, "student")
        assert (file.owner(), file.group()) == ("student", "student")

        file.chown(0, 0) # uid for root
        assert (file.owner(), file.group()) == ("root", "root")

    def test_chown_chmod_run_as_root(self, tmp_path):
        os.chdir(tmp_path)

        file = File("a.txt")
        file.create()
        assert (file.owner(), file.group()) == ("root", "root")

        with change_user("student"):
            file.chmod("o-rwx")
            # TODO use permissions object once I've added that
            assert stat.S_IMODE(os.stat(file).st_mode) == 0o660
    
        with change_user("student"):
            file.chown("student", "student")
            assert (file.owner(), file.group()) == ("student", "student")