import pytest
from shell_adventure.tutorial import Tutorial
from shell_adventure import docker_helper
from textwrap import dedent
from pathlib import Path, PurePosixPath
import datetime, time
import docker, docker.errors
from .helpers import *
from shell_adventure_shared.tutorial_errors import *

class TestIntegration:
    def test_basic(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                        - puzzles.move2
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            assert docker_helper.client.containers.get(tutorial.container.id) != None

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
            docker_helper.client.containers.get(tutorial.container.id)

    def test_random(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.random_puzzle
                content_sources:
                    - content.txt
            """,
            # Use default name generation.
            "content.txt": "STUFF1\n\nSTUFF2\n\nSTUFF3\n",
            "puzzles.py": dedent("""
                from shell_adventure_docker import *
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
            """),
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

    def test_user(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.user_puzzle
            """,
            "puzzles.py": dedent("""
                from shell_adventure_docker import *
                import getpass

                def user_puzzle():
                    fileA = File("A").create()
                    assert fileA.owner() == "student" # euid is student so files get created as student
                    assert getpass.getuser() == "root" # But we are actually running as root

                    with change_user("root"):
                        fileB = File("B").create()
                        assert fileB.owner() == "root"
                
                    return Puzzle(
                        question = "Who are you?",
                        checker = lambda: getpass.getuser() == "root" # checker functions are also run as root
                    )
            """),
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            # Check that the bash session is running as student in /home/student
            exit_code, output = tutorial.container.exec_run("ps -o uname= 1", user = "root")
            assert output.decode().strip() == "student"
            assert tutorial.get_student_cwd() == Path("/home/student")

            puzzle = tutorial.get_all_puzzles()[0]
            solved, feedback = tutorial.solve_puzzle(puzzle)
            assert solved == True
    
    def test_different_user(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                home: /
                user: root
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puz:
                resources:
                    resource.txt: resource.txt
            """,
            "puzzles.py": dedent("""
                from shell_adventure_docker import *

                def puz(home):
                    src = home / "A.txt"
                    src.write_text("A")
                    assert src.owner() == "root"
                    dst = home / "B.txt"

                    def checker(cwd):
                        assert cwd == File("/")
                        return not src.exists() and dst.exists()

                    return Puzzle(
                        question = f"{src} -> {dst}",
                        checker = checker
                    )
            """),
            "resource.txt": "resource!",
        })
        assert tutorial.home == PurePosixPath("/")
        assert tutorial.user == "root"

        # If user isn't root, trying to add file to root will fail
        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            # Check that the bash session is running as root in /
            exit_code, output = tutorial.container.exec_run("ps -o uname= 1", user = "root")
            assert output.decode().strip() == "root"
            assert tutorial.get_student_cwd() == Path("/")

            assert file_exists(tutorial, "/A.txt") # Generate the puzzles in root 
            code, owner = tutorial.container.exec_run("stat -c '%U' A.txt", workdir="/")
            assert owner.decode().strip() == "root"

            code, owner = tutorial.container.exec_run("stat -c '%U' resource.txt", workdir="/")
            assert owner.decode().strip() == "root"

    def test_setup_and_resources(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                resources:
                    resource1.txt: output.txt # Relative to home
                    resource2.txt: /home/student/file2.txt
                setup_scripts:
                    - setup.sh
                    - dir/setup.py
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puzzle:
            """,
            "puzzles.py": dedent(r"""
                from shell_adventure_docker import *

                def puzzle():
                    output = File("output.txt")
                    output.write_text(output.read_text() + "generator\n")

                    return Puzzle(
                        question = f"WRONG",
                        checker = lambda: False,
                    )
            """),
            "setup.sh": r"""
                #!/bin/bash
                OUTPUT="$SHELL:$(pwd):$(whoami)"
                echo $OUTPUT >> output.txt
            """.strip(),
            "dir/setup.py": dedent(r"""
                from shell_adventure_docker import *
                import os, getpass, pwd

                rand.paragraphs(3) # check that this is not null
                output = File("output.txt")
                effective_user = pwd.getpwuid(os.geteuid()).pw_name
                output.write_text(output.read_text() + f"python:{os.getcwd()}:{effective_user}:{getpass.getuser()}\n")
            """),
            "resource1.txt": "resource\n",
            "resource2.txt": "2",
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            exit_code, output = tutorial.container.exec_run(["cat", "output.txt"])
            assert output.decode().splitlines() == ['resource', '/bin/bash:/home/student:root', 'python:/home/student:student:root', 'generator']

            exit_code, output = tutorial.container.exec_run(["cat", "file2.txt"])
            assert output.decode() == "2"

            code, owner = tutorial.container.exec_run("stat -c '%U' file2.txt")
            assert owner.decode().strip() == "student"

    def test_exception(self, tmp_path):
        # Test that exceptions in the container get raised in the Tutorial
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puzzle:
            """,
            "puzzles.py": dedent("""
                def puzzle():
                    raise ValueError('BOOM!')
            """),
        })

        with pytest.raises(UserCodeError, match = "Puzzle generation failed") as exc_info:
            with tutorial: 
                pass # Just launch
        
        expected = dedent("""
            Puzzle generation failed:
              Traceback (most recent call last):
                File "<string>", line 3, in puzzle
              ValueError: BOOM!
        """).lstrip()
        assert str(exc_info.value) == expected

        orig_e = exc_info.value.original_exc
        assert type(orig_e) == ValueError
        assert str(orig_e) == "BOOM!"

    def test_different_image(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                image: shell-adventure/tests:alpine
                resources:
                    resource.txt: resource.txt
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.user_puzzle:
            """,
            "puzzles.py": dedent("""
                from shell_adventure_docker import *
                import getpass

                def user_puzzle():
                    fileA = File("A").create()
                    assert fileA.owner() == "bob"
                    assert getpass.getuser() == "root" # But we are actually running as root

                    with change_user("root"):
                        fileB = File("B").create()
                        assert fileB.owner() == "root"
                
                    return Puzzle(
                        question = "Who are you?",
                        checker = lambda: getpass.getuser() == "root"
                    )
            """),
            "resource.txt": "resource\n",
        })

        with tutorial:
            tutorial.commit()

            assert tutorial.home == Path("/home/bob") # take defaults from container
            assert tutorial.user == "bob"
            exit_code, output = tutorial.container.exec_run("ps -o user=", user = "root")
             # alpine's ps can't filter by pid, it just gives a list of all processes. We want the first (PID 1)
            assert output.decode().splitlines()[0] == "bob"
            assert tutorial.get_student_cwd() == Path("/home/bob")

            code, owner = tutorial.container.exec_run("stat -c '%U' /home/bob/resource.txt")
            assert owner.decode().strip() == "bob"

            run_command(tutorial, "touch A.txt")
            puzzle = tutorial.get_all_puzzles()[0]
            assert tutorial.solve_puzzle(puzzle) == (True, "Correct!")

            tutorial.restart()
            assert not file_exists(tutorial, "A.txt")
