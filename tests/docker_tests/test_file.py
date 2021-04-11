from re import sub
import pytest
import os, stat
from shell_adventure_docker.file import File
from shell_adventure_docker.permissions import Permissions, change_user
from shell_adventure_docker.random_helper import RandomHelper

class TestFile:
    def test_basic(self, working_dir):
        dir = File("A")
        file = dir / "a.txt"
        assert isinstance(file, File)
        
        file = File(working_dir, "b.txt")
        assert file.exists() == False
        file.write_text("STUFF")
        assert file.read_text() == "STUFF"

    def test_path(self, working_dir):
        file = File("A/B.txt")
        assert file.path.startswith("/")
        assert file.path.endswith("A/B.txt")

    def test_create(self, working_dir):
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

        file = File("A/E.txt")
        file.create(content = "STUFF")
        assert file.exists()
        assert file.read_text() == "STUFF"

    def test_children(self, working_dir):
        dir = File("dir")
        for name in ["A.txt", "B.txt", "C.txt"]:
            (dir / name).create()

        with pytest.raises(NotADirectoryError):
            (dir / "A.txt").children
        
        assert isinstance(dir.children, list)
        assert isinstance(dir.children[0], File)

        names = {f.name for f in dir.children}
        assert names == {"A.txt", "B.txt", "C.txt"}

    def test_chmod(self, working_dir):
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

    def test_chmod_errors(self, working_dir):
        file = File("a.txt")

        with pytest.raises(FileNotFoundError):
            file.chmod(0o000)
        with pytest.raises(FileNotFoundError):
            file.chmod("u+g")
        file.create()

        with pytest.raises(Exception, match="Invalid mode"):
            file.chmod("not-a-chmod-string")

    def test_chown(self, working_dir):
        file = File("a.txt")
        file.create()
        assert (file.owner(), file.group()) == ("root", "root")

        file.chown("student")
        assert (file.owner(), file.group()) == ("student", "root")

        file.chown(None, "student")
        assert (file.owner(), file.group()) == ("student", "student")

        file.chown(0, 0) # uid for root
        assert (file.owner(), file.group()) == ("root", "root")

    def test_chown_chmod_run_as_root(self, working_dir):
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

    def test_checking_setting_permissions(self, working_dir):
        file = File("root_file.txt")
        file.create(mode=0o764)

        assert file.permissions.user.read == True
        assert file.permissions.group.write == True

        file.permissions.group.execute = True
        assert file.permissions.group.execute == True
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o774

        file.permissions.group.write = False
        assert int(file.permissions) == 0o754
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o754

    def test_setting_permissions_with_int(self, working_dir):
        file = File("file.txt")
        file.create(mode=0o000)

        file.permissions = 0o666
        assert file.permissions.user.write == True
        assert stat.S_IMODE(os.stat("file.txt").st_mode) == 0o666

        file.permissions.others.write = False # Still "linked" to the actual file
        assert stat.S_IMODE(os.stat("file.txt").st_mode) == 0o664

    def test_setting_permissions_with_object(self, working_dir):
        file = File("file.txt")
        file.create(mode=0o000)

        file.permissions = Permissions(0o666)
        assert file.permissions.user.write == True
        assert stat.S_IMODE(os.stat("file.txt").st_mode) == 0o666

        file.permissions.others.write = False # Still "linked" to the actual file
        assert stat.S_IMODE(os.stat("file.txt").st_mode) == 0o664

    def test_random(self, working_dir):
        try:
            working_dir = File(working_dir)

            File._random = RandomHelper("a\nb\nc")
            subfile = working_dir.random_folder(depth = 1)
            assert subfile.parent == working_dir

            new_folder = working_dir / "my_new_folder"
            new_folder.mark_shared()
            assert new_folder in File._random._shared_folders

            new_file = working_dir.random_file("txt")
            assert new_file.parent == working_dir
            assert new_file.name in ["a.txt", "b.txt", "c.txt"]
        finally:
            File._random = None
