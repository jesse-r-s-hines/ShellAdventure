import pytest
from shell_adventure.host_side.tutorial import Tutorial
from shell_adventure.host_side import docker_helper
from shell_adventure.shared.tutorial_errors import *
from textwrap import dedent
from .helpers import *

class TestRestart:
    def test_restart_disabled(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puz:
                restart_enabled: no
            """,
            "puzzles.py": dedent("""
                from shell_adventure.api import *

                def puz(home):
                    src = home / "A.txt"
                    dst = home / "B.txt"

                    def checker():
                        return not src.exists() and dst.exists()

                    return Puzzle(
                        question = f"{src} -> {dst}",
                        checker = checker
                    )
            """),
        })

        # If user isn't root, trying to add file to root will fail
        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            assert tutorial.restart_enabled == False
            assert tutorial._snapshot == None

            run_command(tutorial, "touch new.txt")
            tutorial.restart()
            assert file_exists(tutorial, "new.txt") # restart should just do nothing

    def test_restart_basic(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                    - custom.py
                puzzles:
                    - puzzles.move
                    - puzzles.move2
                    - custom.tutorial_is_set
            """,
            "puzzles.py": SIMPLE_PUZZLES,
            "custom.py": dedent("""
                import shell_adventure.api
                from shell_adventure.api import *

                def tutorial_is_set():
                    return Puzzle(
                        question = f"Home",
                        checker = lambda: shell_adventure.api._tutorial != None,
                    )
            """),
        })

        # Get the number of images before we made the tutorial
        images_before = docker_helper.client.images.list(all = True)
        containers_before = docker_helper.client.containers.list(all = True)

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            [move1, move2, tut_is_set] = tutorial.get_all_puzzles()

            run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(move1) == (True, "Correct!")

            run_command(tutorial, "mv C.txt D.txt\n")
            assert tutorial.solve_puzzle(move2) == (True, "Correct!")

            assert tutorial.solve_puzzle(tut_is_set) == (True, "Correct!") # _tutorial is set

            tutorial.restart()
            assert all(p.solved == False for p in tutorial.get_all_puzzles()) # all puzzles unsolved again
            assert file_exists(tutorial, "A.txt")
            assert not file_exists(tutorial, "B.txt")

            run_command(tutorial, "mv C.txt D.txt\n")
            assert tutorial.solve_puzzle(move2) == (True, "Correct!")

            assert tutorial.solve_puzzle(tut_is_set) == (True, "Correct!") # _tutorial is still set

        # Assert that we cleaned up our containers
        images_after = docker_helper.client.images.list(all = True)
        containers_after = docker_helper.client.containers.list(all = True)
        assert len(images_before) == len(images_after)
        assert len(containers_before) == len(containers_after)

    def test_restart_pickle_failure(self, tmp_path):
        puzzles = dedent("""
            from shell_adventure.api import *

            def unpicklable():
                gen = (i for i in range(1, 10))
                return Puzzle(
                    question = f"Unpickleable",
                    checker = lambda: gen != None,
                )
        """)  

        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.unpicklable
                restart_enabled: true
            """,
            "puzzles.py": puzzles,
        })

        with pytest.raises(UserCodeError, match="Unpickleable autograder function"):
            with tutorial: pass

        tutorial = create_tutorial(tmp_path, {
                "config.yaml": """
                    modules:
                        - puzzles.py
                    puzzles:
                        - puzzles.unpicklable
                    restart_enabled: False
                """,
                "puzzles.py": puzzles,
            })
        with tutorial:
            assert tutorial.restart_enabled == False
            [puz] = tutorial.get_all_puzzles()
            assert tutorial.solve_puzzle(puz) == (True, "Correct!")

