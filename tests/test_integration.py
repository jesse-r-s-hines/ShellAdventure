#TODO
import pytest
from shell_adventure.tutorial import Tutorial
from textwrap import dedent
from pathlib import Path
import subprocess, datetime, time
import docker, docker.errors

PUZZLES = dedent("""
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

    def cd_puzzle():
        dir = File("dir")
        dir.mkdir()

        def checker(cwd):
            return cwd == dir.resolve()

        return Puzzle(
            question = f"cd into dir.",
            checker = checker
        )
""")

class TestIntegration:
    def test_basic(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move
                    - puzzles.cd_puzzle
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            assert docker.from_env().containers.get(tutorial.container.id) != None

            # Puzzles were generated
            for pt in tutorial.puzzles:
                assert pt.puzzle != None

            assert tutorial.total_score() == 3
            assert tutorial.current_score() == 0

            tutorial.container.exec_run(["mv", "A.txt", "B.txt"])

            move_puzzle = tutorial.puzzles[0].puzzle
            solved, feedback = tutorial.solve_puzzle(move_puzzle)
            assert solved == True
            assert move_puzzle.solved == True
            assert feedback == "Correct!"

            assert tutorial.total_score() == 3
            assert tutorial.current_score() == 2
            assert tutorial.is_finished() == False
            assert tutorial.time() > datetime.timedelta(0)

        # check that the timer gets stopped and doesn't continue advancing after tutorial ends.
        end = tutorial.time()
        time.sleep(0.1)
        assert end == tutorial.time()

        # Make sure the container was removed.
        with pytest.raises(docker.errors.NotFound):
            docker.from_env().containers.get(tutorial.container.id)

    def test_cwd(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.cd_puzzle
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            # Connect to bash
            bash = subprocess.Popen(["docker", "exec", "-i", "-w", "/home/student/dir", tutorial.container.id, "bash"],
                stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            assert tutorial.connect_to_shell("bash") > 1

            cwd_puzzle = tutorial.puzzles[0].puzzle
            solved, feedback = tutorial.solve_puzzle(cwd_puzzle)
            assert solved == True
            assert cwd_puzzle.solved == True
            assert feedback == "Correct!"

            assert tutorial.current_score() == 1
            assert tutorial.is_finished() == True

            assert tutorial.get_student_cwd() == Path("/home/student/dir")
