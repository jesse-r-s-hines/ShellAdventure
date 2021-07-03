import pytest
from shell_adventure.tutorial import Tutorial
from shell_adventure import docker_helper
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
                from shell_adventure_docker import *

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
                import shell_adventure_docker
                from shell_adventure_docker import *

                def tutorial_is_set():
                    return Puzzle(
                        question = f"Home",
                        checker = lambda: shell_adventure_docker._tutorial != None,
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
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.unpicklable
                restart_enabled: true
            """,
            "puzzles.py": dedent("""
                from shell_adventure_docker import *

                def unpicklable():
                    gen = (i for i in range(1, 10))
                    return Puzzle(
                        question = f"Can't pickle generators",
                        checker = lambda: gen == None,
                    )
            """)  
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            puz = tutorial.get_all_puzzles()[0]
            assert puz.checker == None

            assert tutorial.restart_enabled == False
            assert tutorial._snapshot == None
