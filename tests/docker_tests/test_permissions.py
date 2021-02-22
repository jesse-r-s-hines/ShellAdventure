import pytest
from shell_adventure_docker.file import File
from shell_adventure_docker.permissions import *
import os, stat

class TestFile:
    def test_creating_permissions(self, tmp_path):
        os.chdir(tmp_path)

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

    def test_checking_permissions(self, tmp_path):
        os.chdir(tmp_path)

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

    def test_setting_permissions(self, tmp_path):
        os.chdir(tmp_path)

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

    def test_permission_equality(self, tmp_path):
        os.chdir(tmp_path)

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

    def test_permission_throws_errors(self, tmp_path):
        os.chdir(tmp_path)

        with pytest.raises(ValueError):
            p = Permissions(user = "z")

        with pytest.raises(ValueError):
            p = Permissions(group = "ww")