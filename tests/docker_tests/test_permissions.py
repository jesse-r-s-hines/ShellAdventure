import pytest
from shell_adventure_docker.file import File
from shell_adventure_docker.permissions import *
import os, stat, getpass

class TestFile:
    def test_creating_permissions(self, working_dir):
        p = Permissions(0o644)
        assert p.user.read == True
        assert p.others.write == False
        assert int(p) == 0o644

        p = Permissions(user = "rwx", group = "r", others = "r")
        assert p.group.read == True
        assert p.others.execute == False
        assert int(p) == 0o744

        p = Permissions(user = "rwx", group = "r")
        assert p.others.read == False
        assert int(p) == 0o740

        file = File("file.txt")
        file.create(0o766)
        p = LinkedPermissions(file)
        assert int(p) == 0o766

    def test_permissions_to_string(self):
        p = Permissions(0o644)
        assert str(p) == "rw-r--r--"

        p = Permissions(user = "rwx", group = "r", others = "rx")
        assert str(p) == "rwxr--r-x"

    def test_checking_permissions(self, working_dir):
        file = File("file.txt")
        file.create(0o766)
        perms = LinkedPermissions(file)

        assert perms.user.read == True
        assert perms.user.write == True
        assert perms.user.execute == True
        assert perms.group.read == True
        assert perms.group.write == True
        assert perms.group.execute == False
        assert perms.others.read == True
        assert perms.others.write == True
        assert perms.others.execute == False

    def test_setting_permissions(self, working_dir):
        file = File("file.txt")
        file.create(0o000)
        perms = LinkedPermissions(file)
        assert perms == Permissions(0o000)

        mode = 0o000
        for perm_group in ["user", "group", "others"]:
            for perm in ["read", "write", "execute"]:
                setattr(getattr(perms, perm_group), perm, True)
                # Assert that the getter/setter works
                assert getattr(getattr(perms, perm_group), perm) == True

                mode = (mode >> 1) | 0o400 # 0o400, 0o600, 0o700, 0o740, 0o760, ...
                assert stat.S_IMODE(os.stat(file).st_mode) == mode, f"Test set bit {perm_group}.{perm} (mode should be {oct(mode)})"

        assert perms == Permissions(0o777)

    def test_permission_equality(self, working_dir):
        p1 = Permissions(0o744)
        p2 = Permissions(user = "rwx", group = "r", others = "r")
        p3 = Permissions(0o444)
        file = File("file")
        file.create(0o744)
        p4 = LinkedPermissions(file)

        assert p1 == p2
        assert p1 != p3
        assert p2 != p3
        assert p1 == p4

        # Permission equality with ints.
        assert p1 == 0o744
        assert p2 == 0o744
        assert p2 != 0o666
        assert (p2 != 0o744) == False

    def test_permission_throws_errors(self, working_dir):
        with pytest.raises(ValueError):
            p = Permissions(user = "z")

        with pytest.raises(ValueError):
            p = Permissions(group = "ww")


    def test_change_user(self, working_dir):
        root_file = File("root_file.txt")
        root_file.create()
        assert (root_file.owner(), root_file.group()) == ("root", "root")

        with change_user("student"):
            student_file = File("student_file.txt")
            student_file.create()
            assert (student_file.owner(), student_file.group()) == ("student", "student")

        # Back to student
        root_file2 = File("root_file2.txt")
        root_file2.create()
        assert (root_file2.owner(), root_file2.group()) == ("root", "root")

    def test_change_user_and_group(self, working_dir):
        with change_user("root", "student"):
            file = File("file.txt")
            file.create()
            assert (file.owner(), file.group()) == ("root", "student")

        # Back to root
        root_file = File("root_file.txt")
        root_file.create()
        assert (root_file.owner(), root_file.group()) == ("root", "root")

    def test_change_back_user(self):
        with change_user("student"):
            assert os.geteuid() == 1000
            with change_user("root"):
                assert os.geteuid() == 0
            assert os.geteuid() == 1000
        assert os.geteuid() == 0

    def test_system_call_change_user(self, working_dir):
        with change_user("student"):
            os.system(f'touch a.txt')
            file = File("a.txt")
            # os.system is NOT affected by change_user currently.
            assert (file.owner(), file.group()) == ("root", "root")