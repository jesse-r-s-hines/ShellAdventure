from typing import List
import pytest
from pathlib import PurePosixPath, Path
import shell_adventure_docker
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.file import File
from shell_adventure_docker.support import Puzzle
import os, subprocess, pickle
from textwrap import dedent;
from shell_adventure_docker.exceptions import *

SIMPLE_PUZZLES = dedent("""
    from shell_adventure_docker import *

    def move():
        file = File("A.txt")
        file.write_text("A")

        def checker():
            return not file.exists() and File("B.txt").exists()

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker
        )
""")


class TestTutorialDockerExceptions:
    def test_puzzle_not_found(self, working_dir):
        with pytest.raises(TutorialConfigException, match="Unknown puzzle generators: mypuzzles.not_a_puzzle"):
            tutorial = pytest.helpers.create_tutorial(working_dir,
                modules = {"mypuzzles": SIMPLE_PUZZLES},
                puzzles = ["mypuzzles.not_a_puzzle"]
            )

    def test_config_error(self, working_dir):
        with pytest.raises(TutorialConfigException, match="doesn't exist"):
            tutorial = pytest.helpers.create_tutorial(working_dir,
                home = "/not/a/dir",
            )

        with pytest.raises(TutorialConfigException, match="doesn't exist"):
            tutorial = pytest.helpers.create_tutorial(working_dir,
                user = "henry",
            )


    def test_puzzle_generator_bad_return(self, working_dir):
        puzzles = dedent("""
            def invalid():
                return "a string"
        """)

        with pytest.raises(UserCodeError, match="Puzzle generator did not return Puzzle"):
            tutorial = pytest.helpers.create_tutorial(working_dir,
                modules = {"mypuzzles": puzzles},
                puzzles = ["mypuzzles.invalid"],
            )

    def test_solve_puzzle_bad_return(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *

            def invalid():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: 100,
                )
        """)
        tutorial = pytest.helpers.create_tutorial(working_dir,
            modules = {"mypuzzles": puzzles},
            puzzles = ["mypuzzles.invalid"],
        )
        [puzzle] = list(tutorial.puzzles.values())

        with pytest.raises(UserCodeError, match="bool or str expected"):
            tutorial.solve_puzzle(puzzle.id)



    def test_bash_script_exception(self, working_dir):
        with pytest.raises(UserCodeError, match="not-a-command: not found"):
            tutorial = pytest.helpers.create_tutorial(working_dir,
                setup_scripts = [
                    ("script.sh", r"""echo hello; not-a-command"""),
                ],
            )

    def test_py_script_exception(self, tmp_path):
        with pytest.raises(UserCodeError, match='Setup script "script.py" failed') as exc_info:
            tutorial = pytest.helpers.create_tutorial(tmp_path, 
                 setup_scripts = [
                    ("script.py", r"""raise TypeError('BOOM!')"""),
                ],
            )

        e = exc_info.value.__cause__
        assert type(e) == TypeError
        assert e.args[0] == "BOOM!"

    def test_generation_exception(self, tmp_path):
        with pytest.raises(UserCodeError, match = "Puzzle generation failed") as exc_info:
            tutorial = pytest.helpers.create_tutorial(tmp_path, 
                modules = {"puzzles": dedent(r"""
                    def puzzle():
                        raise ValueError('BOOM!')
                """)},
                puzzles = ["puzzles.puzzle"],
            )

        e = exc_info.value.__cause__
        assert type(e) == ValueError
        assert e.args[0] == "BOOM!"

    def test_module_exception(self, tmp_path):
        with pytest.raises(UserCodeError, match = "Puzzle generation failed") as exc_info:
            tutorial = pytest.helpers.create_tutorial(tmp_path,
                modules = {"puzzles": dedent(r"""
                    ++ syntax error
                """)},
                puzzles = ["puzzles.puzzle"],
            )

        e = exc_info.value.__cause__
        assert type(e) == SyntaxError

    def test_checker_exception(self, tmp_path):
        tutorial = pytest.helpers.create_tutorial(tmp_path, 
            modules = {"puzzles": dedent(r"""
                from shell_adventure_docker import *

                def puzzle():
                    def checker():
                        raise ValueError("BOOM!")

                    return Puzzle(
                        question = f"Puzzle",
                        checker = checker,
                    )
            """)},
            puzzles = ["puzzles.puzzle"],
        )

        puz_id = list(tutorial.puzzles.keys())[0]
        with pytest.raises(UserCodeError, match = "Puzzle autograder failed") as exc_info:
            tutorial.solve_puzzle(puz_id)

        e = exc_info.value.__cause__
        assert type(e) == ValueError
        assert e.args[0] == "BOOM!"