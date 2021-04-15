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

    def cd_puzzle():
        dir = File("dir")
        dir.mkdir()

        def checker(cwd):
            return cwd == dir.resolve()

        return Puzzle(
            question = f"cd into dir",
            checker = checker
        )

    def random_puzzle(home):
        src = home.random_file("txt")
        src.write_text(rand.paragraphs(3))
        
        dst = home.random_folder().random_file("txt") # Don't create yet

        def checker():
            return not src.exists() and dst.exists()

        return Puzzle(
            question = f"{src} -> {dst}",
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
                    - puzzles.move:
                        - puzzles.move2
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            assert docker.from_env().containers.get(tutorial.container.id) != None

            # Puzzles were generated
            for pt in tutorial.puzzles:
                for pt2 in pt:
                    assert pt2.puzzle != None

            assert [p.question for p in tutorial.get_current_puzzles()] == ["Rename A.txt to B.txt"]
            assert [p.question for p in tutorial.get_all_puzzles()] == ["Rename A.txt to B.txt", "Rename C.txt to D.txt"]

            assert tutorial.total_score() == 5
            assert tutorial.current_score() == 0

            tutorial.container.exec_run(["mv", "A.txt", "B.txt"])

            move_puzzle = tutorial.get_current_puzzles()[0]
            solved, feedback = tutorial.solve_puzzle(move_puzzle)
            assert solved == True
            assert move_puzzle.solved == True
            assert feedback == "Correct!"

            assert tutorial.total_score() == 5
            assert tutorial.current_score() == 2
            assert tutorial.is_finished() == False

            assert [p.question for p in tutorial.get_current_puzzles()] == ["Rename A.txt to B.txt", "Rename C.txt to D.txt"]
            assert [p.question for p in tutorial.get_all_puzzles()] == ["Rename A.txt to B.txt", "Rename C.txt to D.txt"]
    
            tutorial.container.exec_run(["mv", "C.txt", "D.txt"])

            move_puzzle2 = tutorial.get_current_puzzles()[1]
            solved, feedback = tutorial.solve_puzzle(move_puzzle2)
            assert solved == True
            assert move_puzzle2.solved == True
            assert feedback == "Correct!"

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

            cwd_puzzle = tutorial.get_all_puzzles()[0]
            solved, feedback = tutorial.solve_puzzle(cwd_puzzle)
            assert solved == True
            assert cwd_puzzle.solved == True
            assert feedback == "Correct!"

            assert tutorial.current_score() == 1
            assert tutorial.is_finished() == True

            assert tutorial.get_student_cwd() == Path("/home/student/dir")

    def test_random(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.random_puzzle
                content_sources:
                    - content.txt
            """,
            # Use default name generation.
            "puzzles.py": PUZZLES,
            "content.txt": "STUFF1\n\nSTUFF2\n\nSTUFF3\n",
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            rand_puzzle = tutorial.get_all_puzzles()[0]
            src, dst = rand_puzzle.question.split(" -> ")

            exit_code, output = tutorial.container.exec_run(["cat", src])
            assert "STUFF" in output.decode()

            solved, feedback = tutorial.solve_puzzle(rand_puzzle)
            assert solved == False

            tutorial.container.exec_run(["mkdir", "--parents", src, str(Path(dst).parent)])
            tutorial.container.exec_run(["mv", src, dst])
            solved, feedback = tutorial.solve_puzzle(rand_puzzle)
            assert solved == True

            assert tutorial.is_finished() == True

    def test_setup(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puzzle:
                setup_scripts:
                    - setup.sh
                    - setup.py
            """,
            "puzzles.py": dedent(r"""
                def puzzle():
                    output = File("output.txt")
                    output.write_text(output.read_text() + "generator\n")

                    return Puzzle(
                        question = f"WRONG",
                        checker = lambda: False,
                    )
            """),
            "setup.sh": r"""
                echo \"$SHELL\" > output.txt
            """,
            "setup.py": dedent(r"""
                output = File("output.txt")
                output.write_text(output.read_text() + "python\n")
            """),
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            exit_code, output = tutorial.container.exec_run(["cat", "output.txt"])
            assert output.decode().splitlines() == ['"/bin/bash"', 'python', 'generator']