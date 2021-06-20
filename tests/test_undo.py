import pytest
from shell_adventure.tutorial import Tutorial
from shell_adventure import docker_helper
from textwrap import dedent

PUZZLES = dedent("""
    from shell_adventure_docker import *

    def move():
        file = File("A.txt")
        file.write_text("A")

        def checker():
            return not file.exists() and File("B.txt").exists()

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker,
            score = 2,
        )

    def move2():
        file = File("C.txt")
        file.write_text("C")

        def checker():
            return not file.exists() and File("D.txt").exists()

        return Puzzle(
            question = f"Rename C.txt to D.txt",
            checker = checker,
            score = 3,
        )
""")

class TestUndo:
    def test_undo_disabled(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puz:
                undo: no
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
            assert tutorial.undo_enabled == False
            tutorial.commit()
            assert len(tutorial.undo_list) == 0 # commit is ignored if undo_enabled is false
            assert tutorial.can_undo() == False
            tutorial.undo(); tutorial.restart() # Undo, restart should just do nothing
            assert tutorial.can_undo() == False

    def test_undo_basic(self, tmp_path):
        # Get the number of images before we made the tutorial
        docker_client = docker_helper.client
        images_before = docker_client.images.list(all = True)
        containers_before = docker_client.containers.list(all = True)

        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit for the initial state.
    
            pytest.helpers.run_command(tutorial, "touch temp\n")
            assert pytest.helpers.file_exists(tutorial, "temp")
            assert len(tutorial.undo_list) == 2
            tutorial.undo()
            assert len(tutorial.undo_list) == 1
            assert not pytest.helpers.file_exists(tutorial, "temp")

            pytest.helpers.run_command(tutorial, "touch B\n")
            pytest.helpers.run_command(tutorial, "touch C\n")
            assert len(tutorial.undo_list) == 3
            tutorial.undo()
            assert not pytest.helpers.file_exists(tutorial, "C")
            assert len(tutorial.undo_list) == 2
            pytest.helpers.run_command(tutorial, "touch D\n")
            assert len(tutorial.undo_list) == 3

            images_during = docker_client.images.list(all = True)
            assert len(images_before) < len(images_during)

        images_after = docker_client.images.list(all = True)
        assert len(images_before) == len(images_after)
        containers_after = docker_client.containers.list(all = True)
        assert len(containers_before) == len(containers_after)

    def test_undo_with_puzzle_solving(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command

            puz1 = tutorial.get_all_puzzles()[0]
            puz2 = tutorial.get_all_puzzles()[1]

            pytest.helpers.run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!")
            assert (puz1.solved, puz2.solved) == (True, False)

            tutorial.undo()
            assert pytest.helpers.file_exists(tutorial, "A.txt") and not pytest.helpers.file_exists(tutorial, "B.txt")
            assert (puz1.solved, puz2.solved) == (False, False) # Puzzle is no longer solved

            pytest.helpers.run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!") # Re-solve puzzle

            pytest.helpers.run_command(tutorial, "mv C.txt D.txt\n")
            assert tutorial.solve_puzzle(puz2) == (True, "Correct!")

            assert tutorial.is_finished()

    def test_undo_empty_stack(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command

            assert len(tutorial.undo_list) == 1
            assert not tutorial.can_undo()
            tutorial.undo() # Should do nothing since we have nothing to undo
            assert len(tutorial.undo_list) == 1

            pytest.helpers.run_command(tutorial, "touch A\n")
            pytest.helpers.run_command(tutorial, "touch B\n")
            pytest.helpers.run_command(tutorial, "touch C\n")
            pytest.helpers.run_command(tutorial, "touch D\n")
            assert len(tutorial.undo_list) == 5
            assert tutorial.can_undo()

            tutorial.undo()
            tutorial.undo()
            tutorial.undo()
            tutorial.undo()
            assert len(tutorial.undo_list) == 1
            assert not tutorial.can_undo()
            tutorial.undo() # Hit the bottom of the undo stack, nothing should happen (only current state in the stack)
            assert len(tutorial.undo_list) == 1

    def test_undo_sets_tutorial(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.set_totrial:
            """,
            "puzzles.py": dedent("""
                import shell_adventure_docker
                from shell_adventure_docker import *

                def set_totrial():
                    return Puzzle(
                        question = f"Home",
                        checker = lambda: shell_adventure_docker._tutorial != None,
                    )
            """),
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command
            puz = tutorial.get_all_puzzles()[0]

            pytest.helpers.run_command(tutorial, "touch A\n")
            assert tutorial.solve_puzzle(puz) == (True, "Correct!")
            tutorial.undo()
            assert tutorial.solve_puzzle(puz) == (True, "Correct!") # Still has _tutorial set

    def test_redo(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command

            puz1 = tutorial.get_all_puzzles()[0]
            puz2 = tutorial.get_all_puzzles()[1]

            pytest.helpers.run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!")

            pytest.helpers.run_command(tutorial, "mv C.txt D.txt\n")
            assert tutorial.solve_puzzle(puz2) == (True, "Correct!")

            tutorial.restart()
            assert len(tutorial.undo_list) == 1
            assert (puz1.solved, puz2.solved) == (False, False)
            assert pytest.helpers.file_exists(tutorial, "A.txt")
            assert pytest.helpers.file_exists(tutorial, "C.txt")

    def test_undo_pickle_failure(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.unpicklable
                undo: true
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

            assert tutorial.undo_enabled == False
            assert len(tutorial.undo_list) == 0

            tutorial.commit()
            assert len(tutorial.undo_list) == 0 # Commit does nothing

