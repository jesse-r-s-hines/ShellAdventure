from typing import List
import pytest
from pathlib import PurePosixPath, Path
import shell_adventure_docker
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.file import File
from shell_adventure_docker.support import Puzzle
import os, pickle
from textwrap import dedent;
from shell_adventure_docker.tutorial_errors import *
from .helpers import *

class TestTutorialDocker:
    def test_creation(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"],
        )

        assert shell_adventure_docker._tutorial is tutorial # should be set
        assert shell_adventure_docker.rand == None # _random should be None after generation is complete
        assert File.home() == working_dir # File.home() should use tutorial home

        [puzzle] = list(tutorial.puzzles.values())
        assert puzzle.question == "Rename A.txt to B.txt"
        assert (working_dir / "A.txt").exists()

    def test_multiple_modules(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {
                "mypuzzles1": SIMPLE_PUZZLES,
                "mypuzzles2": SIMPLE_PUZZLES,
            },
            puzzles = ["mypuzzles1.move", "mypuzzles2.move"],
        )

        assert len(tutorial.puzzles) == 2

    def test_empty(self, working_dir):
        tutorial = create_tutorial(working_dir, modules = {}, puzzles = [])
        assert tutorial.puzzles == {}

    def test_get_generators(self):
        module = TutorialDocker._create_module("mypuzzles", SIMPLE_PUZZLES)
        generators = TutorialDocker._get_generators_from_module(module)
        assert list(generators.keys()) == ["mypuzzles.move"]

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

        module = TutorialDocker._create_module("mypuzzles", puzzles)
        generators = TutorialDocker._get_generators_from_module(module)
        assert list(generators.keys()) == ["mypuzzles.move"]

    def test_restore(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"]
        )
        puzzles: List[Puzzle] = list(tutorial.puzzles.values())
        puzzles = pickle.loads(pickle.dumps(puzzles)) # Emulate sending/receiving the puzzles
        puz = puzzles[0].id

        tutorial = TutorialDocker()
        tutorial.restore(home = working_dir, user = "student", puzzles = puzzles)

        assert tutorial.solve_puzzle(puz) == (False, "Incorrect!")
        os.system("mv A.txt B.txt")
        assert tutorial.solve_puzzle(puz) == (True, "Correct!")


    def test_user(self, working_dir): 
        tutorial = create_tutorial(working_dir,
            user = "student",
            modules = {"mypuzzles": dedent("""
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

        assert File("studentFile").owner() == "student" # euid is student so files get created as student
        assert File("rootFile").owner() == "root"

        [puzzle] = list(tutorial.puzzles.values())
        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")

    def test_root_user(self, working_dir): 
        tutorial = create_tutorial(working_dir,
            user = "root",
            modules = {"mypuzzles": SIMPLE_PUZZLES},
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


    def test_setup_scripts(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": dedent(r"""
                from shell_adventure_docker import *

                def puzzle():
                    output = File("output.txt")
                    output.write_text(output.read_text() + "generator\n")

                    return Puzzle(
                        question = f"WRONG",
                        checker = lambda: False,
                    )
            """)},
            puzzles = ["mypuzzles.puzzle"],
            setup_scripts = [
                ("script.sh", r"""
                    #!/bin/bash
                    OUTPUT="$SHELL:$(pwd):$(whoami)"
                    su student -c "echo '$OUTPUT' >> output.txt"
                """.strip()),
                ("path/to/script.sh", r"""
                    #!/bin/bash
                    echo 'script2.sh' >> output.txt
                """.strip()), # Duplicate names should still work (name is just for display purposes)
                ("script.py", dedent(r"""
                    from shell_adventure_docker import *
                    import os, getpass, pwd

                    rand.paragraphs(3) # check that this is not null
                    output = File("output.txt")
                    effective_user = pwd.getpwuid(os.geteuid()).pw_name
                    output.write_text(output.read_text() + f"python:{os.getcwd()}:{effective_user}:{getpass.getuser()}\n")
                """)),
                ("path/to/script.py", dedent(r"""
                    from shell_adventure_docker import *
                    output = File("output.txt")
                    output.write_text(output.read_text() + "script2.py\n")
                """)),
            ]
        )

        output = working_dir / "output.txt"
        assert output.read_text().splitlines() == [
            f'/bin/bash:{working_dir}:root',
            'script2.sh',
            f'python:{working_dir}:student:root',
            'script2.py',
            'generator'
        ]
        assert (output.owner(), output.group()) == ("student", "student")
 
    def test_resources(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"],
            resources = {
                PurePosixPath("resource1.txt"): b"RESOURCE1",
                PurePosixPath(f"{working_dir}/resource2.txt"): b"RESOURCE2",
                PurePosixPath(f"/resource3.txt"): b"RESOURCE3", # File will be created in root, with student as owner
            }
        )
        r1 = working_dir / "resource1.txt"
        r2 = working_dir / "resource2.txt"
        r3 = Path("/resource3.txt")

        assert (r1.owner(), r1.group()) == ("student", "student")
        assert r1.read_text() == "RESOURCE1"
        assert (r2.owner(), r2.group()) == ("student", "student")
        assert r2.read_text() == "RESOURCE2"
        assert (r3.owner(), r3.group()) == ("student", "student")
        assert r3.read_text() == "RESOURCE3"

    def test_resources_different_user(self, working_dir):
        tutorial = create_tutorial(working_dir,
            user = "root",
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"],
            resources = {
                PurePosixPath("resource1.txt"): b"RESOURCE1", # Relative to home
                PurePosixPath(working_dir, "resource2.txt"): b"RESOURCE2",
            }
        )

        assert (working_dir / "resource1.txt").owner() == "root"
        assert (working_dir / "resource1.txt").read_text() == "RESOURCE1"
        assert (working_dir / "resource2.txt").owner() == "root"
        assert (working_dir / "resource2.txt").read_text() == "RESOURCE2"

    def test_resources_create_dirs(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"],
            resources = {
                PurePosixPath(f"{working_dir}/dir/resource.txt"): b"RESOURCE",
            }
        )
        assert (working_dir / "dir/resource.txt").exists()
