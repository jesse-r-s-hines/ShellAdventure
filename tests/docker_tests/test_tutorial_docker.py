from typing import List
import pytest
from pathlib import PurePosixPath, Path, PurePath
import shell_adventure_docker
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.file import File
from shell_adventure_shared.puzzle import Puzzle
from shell_adventure_docker.random_helper import RandomHelperException
import os, pickle
from textwrap import dedent;
from shell_adventure_shared.tutorial_errors import *
from .helpers import *

class TestTutorialDocker:
    def test_creation(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"],
        )

        assert shell_adventure_docker._tutorial is tutorial # should be set
        assert tutorial.rand == None # _random should be None after generation is complete
        with pytest.raises(RandomHelperException):
            shell_adventure_docker.rand()

        assert File.home() == working_dir # File.home() should use tutorial home

        [puzzle] = list(tutorial.puzzles.values())
        assert puzzle.question == "Rename A.txt to B.txt"
        assert (working_dir / "A.txt").exists()

    def test_multiple_modules(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {
                PurePath("mypuzzles1.py"): SIMPLE_PUZZLES,
                PurePath("mypuzzles2.py"): SIMPLE_PUZZLES,
            },
            puzzles = ["mypuzzles1.move", "mypuzzles2.move"],
        )

        assert len(tutorial.puzzles) == 2

    def test_empty(self, working_dir):
        tutorial = create_tutorial(working_dir, modules = {}, puzzles = [])
        assert tutorial.puzzles == {}

    def test_get_templates(self):
        module = TutorialDocker._create_module(PurePath("mypuzzles.py"), SIMPLE_PUZZLES)
        templates = TutorialDocker._get_templates_from_module(module)
        assert list(templates.keys()) == ["mypuzzles.move"]

    def test_private_methods_arent_puzzles(self):
        puzzles = dedent("""
            from shell_adventure_docker import *
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

    def test_restore(self, working_dir):
        modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES}
        tutorial = create_tutorial(working_dir,
            modules = modules,
            puzzles = ["mypuzzles.move"]
        )
        puzzles: List[Puzzle] = list(tutorial.puzzles.values())
        puzzles = pickle.loads(pickle.dumps(puzzles)) # Emulate sending/receiving the puzzles
        puz = puzzles[0].id

        tutorial = TutorialDocker()
        tutorial.restore(
            home = working_dir, user = "student",
            modules = modules, puzzles = puzzles
        )

        assert tutorial.solve_puzzle(puz) == (False, "Incorrect!")
        os.system("mv A.txt B.txt")
        assert tutorial.solve_puzzle(puz) == (True, "Correct!")


    def test_user(self, working_dir): 
        tutorial = create_tutorial(working_dir,
            user = "student",
            modules = {PurePath("mypuzzles.py"): dedent("""
                from shell_adventure_docker import *
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

    def test_root_user(self, working_dir): 
        tutorial = create_tutorial(working_dir,
            user = "root",
            modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"]
        )
        assert (working_dir / "A.txt").owner() == "root"


    def test_student_cwd(self, working_dir):
        tutorial = create_tutorial(working_dir)
        assert tutorial.student_cwd() == File("/home/student") # Gets the cwd from the bash session

    def test_get_files(self, working_dir):
        tutorial = create_tutorial(working_dir, puzzles = [])

        a = File("A"); a.mkdir()
        File("A/B").create()
        File("C").create()
        File("D").symlink_to(a)

        files = tutorial.get_files(working_dir)
        assert all([f.is_absolute() for _, _, f in files])
        assert set(files) == {(True, False, working_dir / "A"), (False, False, working_dir / "C"), (True, True, working_dir / "D")}

    def test_get_special_files(self, working_dir):
        tutorial = create_tutorial(working_dir)
        
        def get_files_recursive(folder):
            all_files = []
            for is_dir, is_symlink, file in tutorial.get_files(folder):
                all_files.append(file)
                if is_dir and not is_symlink:
                    all_files.extend(get_files_recursive(file))
            return all_files

        # /proc has special files that sometimes throws errors when trying to get them via python. Test that they are handled properly.
        assert get_files_recursive("/proc") != []

    def test_puzzle_generation_order(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {PurePath("puzzles.py"): dedent(r"""
                from shell_adventure_docker import *

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
 

