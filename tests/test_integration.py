import pytest
from shell_adventure.host_side import docker_helper
from shell_adventure.shared.tutorial_errors import *
from textwrap import dedent
from pathlib import Path, PurePosixPath
import datetime, time
import docker, docker.errors
from .helpers import *

class TestIntegration:
    def test_basic(self, tmp_path: Path, check_containers):
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

        with tutorial: # Context manager will start and stop the container
            assert docker_helper.client.containers.get(tutorial.container.id) != None

            # Puzzles were generated
            assert tutorial.puzzles[0].data.template == "puzzles.move"
            assert tutorial.puzzles[0][0].data.template == "puzzles.move2"

            assert [p.question for p in tutorial.get_current_puzzles()] == ["Rename A.txt to B.txt"]
            assert [p.question for p in tutorial.get_all_puzzles()] == ["Rename A.txt to B.txt", "Rename C.txt to D.txt"]

            assert tutorial.total_score() == 5
            assert tutorial.current_score() == 0

            home = PurePosixPath("/home/student")
            expected = [".profile", ".bash_logout", ".bashrc", "A.txt", "C.txt"]
            files = tutorial.get_files(home)
            assert set(files) == {(False, False, home / f) for f in expected}

            run_command(tutorial, "mv A.txt B.txt")

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

            run_command(tutorial, "mv C.txt D.txt")

            move_puzzle2 = tutorial.get_current_puzzles()[1]
            solved, feedback = tutorial.solve_puzzle(move_puzzle2)
            assert solved == True
            assert move_puzzle2.solved == True
            assert feedback == "Correct!"
            assert tutorial.is_finished() == True

            assert tutorial.time() > datetime.timedelta(0)

        # check that the timer gets stopped and doesn't continue advancing after tutorial ends.
        end = tutorial.time()
        time.sleep(0.1)
        assert end == tutorial.time()

        # Make sure the container was removed.
        with pytest.raises(docker.errors.NotFound):
            docker_helper.client.containers.get(tutorial.container.id)

    def test_random(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.random_puzzle
                    - puzzles.rand_not_in_checker
                content_sources:
                    - content.txt
            """,
            # Use default name generation.
            "content.txt": "STUFF1\n\nSTUFF2\n\nSTUFF3\n",
            "puzzles.py": dedent("""
                from shell_adventure.api import *
                def random_puzzle(home):
                    src = home.random_file("txt")
                    src.write_text(rand().paragraphs(3))

                    dst = home.random_shared_folder().random_file("txt") # Don't create yet

                    def checker():
                        return not src.exists() and dst.exists()

                    return Puzzle(
                        question = f"{src} -> {dst}",
                        checker = checker
                    )

                def rand_not_in_checker(home):
                    return Puzzle(question = "", checker = lambda: rand().name())
            """),
        })

        with tutorial:
            [rand_puzzle, rand_not_in_checker]  = tutorial.get_all_puzzles()
            src, dst = rand_puzzle.question.split(" -> ")

            exit_code, output = run_command(tutorial, ["cat", src])
            assert "STUFF" in output

            solved, feedback = tutorial.solve_puzzle(rand_puzzle)
            assert solved == False

            run_command(tutorial, ["mkdir", "--parents", src, str(PurePosixPath(dst).parent)])
            run_command(tutorial, ["mv", src, dst])
            solved, feedback = tutorial.solve_puzzle(rand_puzzle)
            assert solved == True

            with pytest.raises(UserCodeError, match = "You can only use randomization in Puzzle templates"):
                tutorial.solve_puzzle(rand_not_in_checker)

    def test_user(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.user_puzzle
            """,
            "puzzles.py": dedent("""
                from shell_adventure.api import *
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

        with tutorial:
            # Check that the bash session is running as student in /home/student
            exit_code, output = run_command(tutorial, "ps -o uname= 1", user = "root")
            assert output == "student"
            assert tutorial.get_student_cwd() == PurePosixPath("/home/student")

            puzzle = tutorial.get_all_puzzles()[0]
            solved, feedback = tutorial.solve_puzzle(puzzle)
            assert solved == True

    def test_different_user(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                container_options:
                    working_dir: /
                    user: root
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puz:
            """,
            "puzzles.py": dedent("""
                from shell_adventure.api import *

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
        })

        # If user isn't root, trying to add file to root will fail
        with tutorial:
            # Check that the bash session is running as root in /
            exit_code, output = run_command(tutorial, "ps -o uname= 1", user = "root")
            assert output == "root"
            assert tutorial.get_student_cwd() == PurePosixPath("/")

            assert file_exists(tutorial, "/A.txt") # The puzzles are generated in root
            code, owner = run_command(tutorial, "stat -c '%U' A.txt", workdir="/")
            assert owner == "root"

    def test_exception(self, tmp_path: Path, check_containers):
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

        # Shouldn't include our code in the traceback, and traceback should show the real path on the host
        expected = dedent(f"""
            Puzzle generation failed for template puzzles.puzzle:
              Traceback (most recent call last):
                File "{tmp_path / 'puzzles.py'}", line 3, in puzzle
                  raise ValueError('BOOM!')
              ValueError: BOOM!
        """).lstrip()
        assert expected == str(exc_info.value)

    def test_container_options(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": f"""
                container_options:
                    command: sh
                    environment:
                        MYVAR: 10
                    volumes:
                        {tmp_path / "volume.txt"}:
                            bind: "/home/student/volume.txt"
                            mode: ro
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move
            """,
            "puzzles.py": SIMPLE_PUZZLES,
            "volume.txt": "Hey a volume!",
        })

        with tutorial:
            # assert that sh was run instead of bash
            exit_code, process = run_command(tutorial, "ps -o comm= 1", user = "root")
            assert process == "sh"

            # Env was set
            exit_code, output = run_command(tutorial, ["sh", "-c", 'echo $MYVAR'])
            assert output == "10"

            # volume exists (and didn't delete our volumes)
            exit_code, output = run_command(tutorial, "cat volume.txt")
            assert output == "Hey a volume!"

    def test_different_image(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                image: shelladventure/tests:alpine
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.user_puzzle:
            """,
            "puzzles.py": dedent("""
                from shell_adventure.api import *
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
        })

        with tutorial:
            exit_code, output = run_command(tutorial, "ps -o user=", user = "root")
             # alpine's ps can't filter by pid, it just gives a list of all processes. We want the first (PID 1)
            assert output.splitlines()[0] == "bob"
            assert tutorial.get_student_cwd() == PurePosixPath("/home/bob")

            puzzle = tutorial.get_all_puzzles()[0]
            assert tutorial.solve_puzzle(puzzle) == (True, "Correct!")

            run_command(tutorial, "touch new.txt")
            tutorial.restart()
            assert not file_exists(tutorial, "new.txt")

    def test_missing_deps(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                image: shelladventure/tests:missing-deps
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        with pytest.raises(ContainerStartupError, match = "dill, python-lorem"):
            with tutorial:
                pass

        assert "dill, python-lorem" in tutorial.logs()

    def test_wrong_user(self, tmp_path: Path, check_containers):
        # Test that exceptions in the container get raised in the Tutorial
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                container_options:
                    user: not-a-user
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
            """,
            "puzzles.py": SIMPLE_PUZZLES
        })

        with pytest.raises(ContainerError, match = "unable to find user not-a-user"):
            with tutorial:
                pass # Just launch

    def test_missing_image(self, tmp_path: Path, check_containers):
        # Test that exceptions in the container get raised in the Tutorial
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                image: not-a-docker-image
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
            """,
            "puzzles.py": SIMPLE_PUZZLES
        })

        with pytest.raises(ContainerStartupError, match = "Not Found .* not-a-docker-image"):
            with tutorial:
                pass # Just launch

    def test_container_dies(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
            """,
            "puzzles.py": SIMPLE_PUZZLES
        })

        with pytest.raises(ContainerStoppedError):
            with tutorial:
                tutorial.container.kill()
                tutorial.get_student_cwd()

    def test_nested_puzzles(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": f"""
                modules:
                    - puzz1.py
                    - puzz2.py
                    - puzz3.py
                    - puzz4.py
                    - puzz5.py
                    - puzz6.py
                puzzles:
                    - puzz1.move:
                        - puzz2.move:
                            - puzz3.move
                    - puzz4.move
                    - puzz5.move:
                        - puzz6.move
            """,
            **{f"puzz{i}.py": SIMPLE_PUZZLES for i in range(1, 7)},
        })

        with tutorial:
            # First level
            assert [n.data.template for n in tutorial.puzzles] == ["puzz1.move", "puzz4.move", "puzz5.move"]

            # Second Level
            assert [n.data.template for n in tutorial.puzzles[0].children] == ["puzz2.move"]
            assert [n.data.template for n in tutorial.puzzles[2].children] == ["puzz6.move"]

            # Third Level
            assert [n.data.template for n in tutorial.puzzles[0][0].children] == ["puzz3.move"]