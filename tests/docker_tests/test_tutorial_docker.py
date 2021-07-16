from typing import List
import pytest
from pathlib import PurePath, Path
import shell_adventure.api
from shell_adventure.docker_side.tutorial_docker import TutorialDocker
from shell_adventure.api.random_helper import RandomHelperException
from shell_adventure.api.file import File
from shell_adventure.shared.puzzle_data import PuzzleData
from shell_adventure.shared.tutorial_errors import *
import os
from textwrap import dedent;
from .helpers import *

class TestTutorialDocker:
    def test_creation(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES},
                puzzles = ["mypuzzles.move"],
            )

            [puzzle] = list(tutorial.puzzles.values())
            assert puzzle.question == "Rename A.txt to B.txt"
            assert puzzle.template == "mypuzzles.move"
            assert (working_dir / "A.txt").exists()

    def test_lifecycle(self, working_dir: Path):
        assert shell_adventure.api._home == None
        assert shell_adventure.api._rand == None

        with TutorialDocker() as tutorial:
            assert shell_adventure.api._home == None # Still none
            assert shell_adventure.api._rand == None

            setup_tutorial(tutorial, working_dir)

            # Sets _rand back after puzzle generation to avoid issues with restore and pickling the rand
            assert shell_adventure.api._home == working_dir
            assert shell_adventure.api._rand == None

            with pytest.raises(RandomHelperException):
                shell_adventure.api.rand()
            assert File.home() == working_dir # File.home() should use tutorial home

        # Both _home and _rand get reset after context manager
        assert shell_adventure.api._home == None
        assert shell_adventure.api._rand == None

    def test_multiple_modules(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {
                    PurePath("mypuzzles1.py"): SIMPLE_PUZZLES,
                    PurePath("mypuzzles2.py"): SIMPLE_PUZZLES,
                },
                puzzles = ["mypuzzles1.move", "mypuzzles2.move"],
            )

            assert len(tutorial.puzzles) == 2

    def test_empty(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir, modules = {}, puzzles = [])
            assert tutorial.puzzles == {}

    def test_get_templates(self):
        module = TutorialDocker._create_module(PurePath("mypuzzles.py"), SIMPLE_PUZZLES)
        templates = TutorialDocker._get_templates_from_module(module)
        assert list(templates.keys()) == ["mypuzzles.move"]

    def test_private_methods_arent_puzzles(self):
        puzzles = dedent("""
            from shell_adventure.api import *
            from os import system # Don't use the imported method as a puzzle.

            def _private_method():
                return "not a puzzle"

            my_lambda = lambda: "not a puzzle"

            def move():
                return Puzzle(
                    question = f"Easiest puzzle ever.",
                    checker = lambda: True,
                )
        """)

        module = TutorialDocker._create_module(PurePath("mypuzzles.py"), puzzles)
        templates = TutorialDocker._get_templates_from_module(module)
        assert list(templates.keys()) == ["mypuzzles.move"]

    def test_restore(self, working_dir: Path):
        modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES}
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = modules,
                puzzles = ["mypuzzles.move"]
            )
            puzzles: List[PuzzleData] = list(tutorial.puzzles.values())
            # Emulate sending/receiving the puzzles
            puzzles = [p.checker_dilled().checker_undilled() for p in puzzles]
            puz = puzzles[0].id

            tutorial = TutorialDocker()
            tutorial.restore(
                home = working_dir, user = "student",
                modules = modules, puzzles = puzzles
            )

            assert tutorial.solve_puzzle(puz) == (False, "Incorrect!")
            os.system("mv A.txt B.txt")
            assert tutorial.solve_puzzle(puz) == (True, "Correct!")


    def test_user(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                user = "student",
                modules = {PurePath("mypuzzles.py"): dedent("""
                    from shell_adventure.api import *
                    import getpass

                    def user_puzzle():
                        File("studentFile").create()
                        assert getpass.getuser() == "root" # But we are actually running as root

                        with change_user("root"):
                            File("rootFile").create()

                        return Puzzle(
                            question = "Who are you?",
                            checker = lambda: getpass.getuser() == "root" # checker functions also run as root
                        )
                """)},
                puzzles = ["mypuzzles.user_puzzle"]
            )

            studentFile = File("studentFile") # euid is student so files get created as student
            assert (studentFile.owner(), studentFile.group()) == ("student", "student")
            rootFile = File("rootFile")
            assert (rootFile.owner(), rootFile.group()) == ("root", "root")

            [puzzle] = list(tutorial.puzzles.values())
            assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")

    def test_root_user(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                user = "root",
                modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES},
                puzzles = ["mypuzzles.move"]
            )
            assert (working_dir / "A.txt").owner() == "root"


    def test_student_cwd(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir)
            assert tutorial.student_cwd() == File("/home/student") # Gets the cwd from the bash session

    def test_get_files(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir, puzzles = [])

            a = File("A"); a.mkdir()
            File("A/B").create()
            File("C").create()
            File("D").symlink_to(a)

            files = tutorial.get_files(working_dir)
            assert all([f.is_absolute() for _, _, f in files])
            assert set(files) == {(True, False, working_dir / "A"), (False, False, working_dir / "C"), (True, True, working_dir / "D")}

    def test_get_special_files(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir)

            def get_files_recursive(folder):
                all_files = []
                for is_dir, is_symlink, file in tutorial.get_files(folder):
                    all_files.append(file)
                    if is_dir and not is_symlink:
                        all_files.extend(get_files_recursive(file))
                return all_files

            # /proc has special files that sometimes throws errors when trying to get them via python. Test that they are handled properly.
            assert get_files_recursive("/proc") != []

    def test_puzzle_generation_order(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {PurePath("puzzles.py"): dedent(r"""
                    from shell_adventure.api import *

                    def puz1():
                        with File("log.txt").open("a") as f: f.write("puz1\n")
                        return Puzzle(question = "", checker = lambda: False)

                    def puz2():
                        with File("log.txt").open("a") as f: f.write("puz2\n")
                        return Puzzle(question = "", checker = lambda: False)

                    def puz3():
                        with File("log.txt").open("a") as f: f.write("puz3\n")
                        return Puzzle(question = "", checker = lambda: False)
                """)},
                puzzles = ["puzzles.puz1", "puzzles.puz3", "puzzles.puz2"],
            )

            log = working_dir / "log.txt"
            assert log.read_text().splitlines() == ['puz1', 'puz3', 'puz2']

    def test_puzzle_always_cwd_in_home(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {PurePath("puzzles.py"): dedent(fr"""
                    from shell_adventure.api import *
                    import os

                    def chdir():
                        os.chdir("/")
                        def checker():
                            os.chdir("/etc")
                            return True
                        return Puzzle(question = "", checker = checker)

                    def checkcwd():
                        assert os.getcwd() == "{working_dir}"
                        return Puzzle(question = "", checker = lambda: os.getcwd() == "{working_dir}")
                """)},
                puzzles = ["puzzles.chdir", "puzzles.checkcwd"],
            )

            [chdir, checkcwd] = tutorial.puzzles.values()
            assert tutorial.solve_puzzle(chdir.id)[0] == True
            assert tutorial.solve_puzzle(checkcwd.id)[0] == True # cwd got changed back

        