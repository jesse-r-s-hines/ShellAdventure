import pytest
from shell_adventure_docker.file import File
import shell_adventure_docker.utilities as utils
import os, getpass

class TestFile:
    def test_change_user(self, tmp_path):
        os.chdir(tmp_path)

        root_file = File("root_file.txt")
        root_file.create()
        assert (root_file.owner(), root_file.group()) == ("root", "root")

        with utils.change_user("student"):
            student_file = File("student_file.txt")
            student_file.create()
            assert (student_file.owner(), student_file.group()) == ("student", "student")

        # Back to student
        root_file2 = File("root_file2.txt")
        root_file2.create()
        assert (root_file2.owner(), root_file2.group()) == ("root", "root")

    def test_change_user_and_group(self, tmp_path):
        os.chdir(tmp_path)

        with utils.change_user("root", "student"):
            file = File("file.txt")
            file.create()
            assert (file.owner(), file.group()) == ("root", "student")

        # Back to root
        root_file = File("root_file.txt")
        root_file.create()
        assert (root_file.owner(), root_file.group()) == ("root", "root")

    def test_change_back_user(self):
        with utils.change_user("student"):
            assert os.geteuid() == 1000
            with utils.change_user("root"):
                assert os.geteuid() == 0
            assert os.geteuid() == 1000
        assert os.geteuid() == 0

    def test_system_call_change_user(self, tmp_path):
        os.chdir(tmp_path)

        with utils.change_user("student"):
            os.system(f'touch a.txt')
            file = File("a.txt")
            # os.system is NOT affected by utils.change_user currently.
            assert (file.owner(), file.group()) == ("root", "root")

