import pytest
import stat
from pathlib import Path
from shell_adventure.api.file import File
from shell_adventure.api.permissions import Permissions, change_user
from shell_adventure.api.random_helper import RandomHelper
import shell_adventure.api

class TestFile:
    def test_basic(self, working_dir: Path):
        dir = File("A")
        file = dir / "a.txt"
        assert isinstance(file, File)

        file = File(working_dir, "b.txt")
        assert file.exists() == False
        file.write_text("STUFF")
        assert file.read_text() == "STUFF"

    def test_path(self, working_dir: Path):
        file = File("A/B.txt")
        assert file.path.startswith("/")
        assert file.path.endswith("A/B.txt")

    def test_create(self, working_dir: Path):
        file = File("A/B.txt")
        assert not file.parent.exists()
        assert not file.exists()

        with pytest.raises(FileNotFoundError):
            file.create(recursive=False)
        created_file = file.create(mode=0o644, recursive=True)
        assert created_file == file

        assert file.exists()
        assert file.parent.exists()
        assert file.permissions == 0o644
        # parents use default permissions.
        assert File("A").permissions == 0o755

        file = File("A/C.txt")
        file.create(mode=0o666, recursive=True)
        assert file.permissions == 0o666
        assert File("A").permissions == 0o755 # Hasn't changed

        file = File("A/D.txt")
        file.create()
        assert file.exists()
        assert file.permissions == 0o644 # Default permissions

        file = File("E/F/G.txt")
        file.create(mode=0o111)
        assert file.exists()
        assert File("E/F").permissions == 0o755 # Default permissions
        assert File("E/F").permissions == 0o755

        file = File("A/E.txt")
        file.create(content = "STUFF")
        assert file.exists()
        assert file.read_text() == "STUFF"

    def test_children(self, working_dir: Path):
        dir = File("dir")
        for name in ["A.txt", "B.txt", "C.txt"]:
            (dir / name).create()

        with pytest.raises(NotADirectoryError):
            (dir / "A.txt").children

        assert isinstance(dir.children, list)
        assert isinstance(dir.children[0], File)

        names = {f.name for f in dir.children}
        assert names == {"A.txt", "B.txt", "C.txt"}

    def test_chmod(self, working_dir: Path):
        file = File("a.txt")
        file.create()

        assert file.permissions == 0o644

        file.chmod(0o000)
        assert file.permissions == 0o000

        file.chmod(0o777)
        assert file.permissions == 0o777

        file.chmod("o-wx,g-wx")
        assert file.permissions == 0o744

        file.chmod("g+w,u=x")
        assert file.permissions == 0o164

    def test_chmod_errors(self, working_dir: Path):
        file = File("a.txt")

        with pytest.raises(FileNotFoundError):
            file.chmod(0o000)
        with pytest.raises(FileNotFoundError):
            file.chmod("u+g")
        file.create()

        with pytest.raises(ValueError, match="Invalid mode"):
            file.chmod("not-a-chmod-string")

    def test_chown(self, working_dir: Path):
        file = File("a.txt")
        file.create()
        assert (file.owner(), file.group()) == ("root", "root")

        file.chown("student")
        assert (file.owner(), file.group()) == ("student", "root")

        file.chown(None, "student")
        assert (file.owner(), file.group()) == ("student", "student")

        file.chown(0, 0) # uid for root
        assert (file.owner(), file.group()) == ("root", "root")

    def test_chown_chmod_run_as_root(self, working_dir: Path):
        file = File("a.txt")
        file.create()
        assert (file.owner(), file.group()) == ("root", "root")

        with change_user("student"):
            file.chmod("o-rwx")
            assert file.permissions == 0o640

        with change_user("student"):
            file.chown("student", "student")
            assert (file.owner(), file.group()) == ("student", "student")

    def test_checking_setting_permissions(self, working_dir: Path):
        file = File("root_file.txt")
        file.create(mode=0o764)

        assert file.permissions.user.read == True
        assert file.permissions.group.write == True

        file.permissions.group.execute = True
        assert file.permissions.group.execute == True
        assert stat.S_IMODE(file.stat().st_mode) == 0o774

        file.permissions.group.write = False
        assert int(file.permissions) == 0o754
        assert stat.S_IMODE(file.stat().st_mode) == 0o754

    def test_setting_permissions_with_int(self, working_dir: Path):
        file = File("file.txt")
        file.create(mode=0o000)

        file.permissions = 0o666 #type: ignore # this confuses mypy https://github.com/python/mypy/issues/3004
        assert file.permissions.user.write == True
        assert stat.S_IMODE(File("file.txt").stat().st_mode) == 0o666

        file.permissions.others.write = False # Still "linked" to the actual file
        assert stat.S_IMODE(File("file.txt").stat().st_mode) == 0o664

    def test_setting_permissions_with_object(self, working_dir: Path):
        file = File("file.txt")
        file.create(mode=0o000)

        file.permissions = Permissions(0o666) #type: ignore # this confuses mypy
        assert file.permissions.user.write == True
        assert stat.S_IMODE(File("file.txt").stat().st_mode) == 0o666

        file.permissions.others.write = False # Still "linked" to the actual file
        assert stat.S_IMODE(File("file.txt").stat().st_mode) == 0o664

    def test_random(self, working_dir: Path):
        try:
            working_dir = File(working_dir)

            # You have to have a tutorial object initialized for randomization to work.
            shell_adventure.api._rand = RandomHelper("a\nb\nc")

            subfile = working_dir.random_shared_folder(depth = 1)
            assert subfile.parent == working_dir

            new_folder = working_dir / "my_new_folder"
            new_folder.mark_shared()
            assert new_folder in shell_adventure.api.rand()._shared_folders

            new_file = working_dir.random_file("txt")
            assert new_file.parent == working_dir
            assert new_file.name in ["a.txt", "b.txt", "c.txt"]
        finally:
            shell_adventure.api._rand = None

    def test_home(self, working_dir: Path):
        assert File.home() == File("/root") # No tutorial set up.


