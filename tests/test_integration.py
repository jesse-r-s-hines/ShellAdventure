from typing import Union, List
import pytest
from shell_adventure.tutorial import Tutorial, TutorialError
from textwrap import dedent
from pathlib import Path
import subprocess, datetime, time
import docker, docker.errors

PUZZLES = dedent("""
    from shell_adventure_docker import *
    import getpass

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

    def user_puzzle():
        return Puzzle(
            question = "Who are you?",
            checker = lambda: getpass.getuser() == "root" # checker functions run as root
        )
""")

def run_command(tutorial: Tutorial, command: Union[str, List[str]]):
    """ Execute a command in a tutorial, make a commit after the command. """
    # I tried using an actual bash session so we could test if the script was getting called
    # but I couldn't get bash to run PROMPT_COMMAND when called via Popen. Using the bash `-i`
    # flag doesn't work either.
    tutorial.container.exec_run(command)
    tutorial.commit()

def file_exists(tutorial: Tutorial, file: str): 
    """ Checks if a file exists in the container. """
    exit_code, output = tutorial.container.exec_run(["test", "-f", file])
    return exit_code == 0 # file exists

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

    def test_user(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.user_puzzle
            """,
            "puzzles.py": PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            puzzle = tutorial.get_all_puzzles()[0]
            solved, feedback = tutorial.solve_puzzle(puzzle)
            assert solved == True
    
    def test_setup_and_resources(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                resources:
                    resource1.txt: output.txt # Relative to home
                    resource2.txt: /home/student/file2.txt
                setup_scripts:
                    - setup.sh
                    - setup.py
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
                echo \"$SHELL\" >> output.txt
            """,
            "setup.py": dedent(r"""
                from shell_adventure_docker import *

                output = File("output.txt")
                output.write_text(output.read_text() + "python\n")
            """),
            "resource1.txt": "resource\n",
            "resource2.txt": "2",
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            exit_code, output = tutorial.container.exec_run(["cat", "output.txt"])
            assert output.decode().splitlines() == ['resource', '"/bin/bash"', 'python', 'generator']

            exit_code, output = tutorial.container.exec_run(["cat", "file2.txt"])
            assert output.decode() == "2"

    def test_bash_script_exception(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                setup_scripts:
                    - setup.sh
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
            """,
            "puzzles.py": PUZZLES,
            "setup.sh": "echo hello; not-a-command"
        })

        with pytest.raises(TutorialError, match="command not found"):
            with tutorial: 
                pass # Just launch

    def test_py_script_exception(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                setup_scripts:
                    - setup.py
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
            """,
            "puzzles.py": PUZZLES,
            "setup.py": "raise Exception('BOOM')"
        })

        with pytest.raises(TutorialError, match="BOOM"):
            with tutorial: 
                pass # Just launch

    def test_generation_exception(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puzzle:
            """,
            "puzzles.py": dedent("""
                def puzzle():
                    raise Exception('BOOM')
            """),
        })

        with pytest.raises(TutorialError, match="BOOM"):
            with tutorial: 
                pass # Just launch
            
    def test_undo_basic(self, tmp_path):
        # Get the number of images before we made the tutorial
        docker_client = docker.from_env()
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
    
            run_command(tutorial, "touch temp\n")
            assert file_exists(tutorial, "temp")
            assert len(tutorial.undo_list) == 2
            tutorial.undo()
            assert len(tutorial.undo_list) == 1
            assert not file_exists(tutorial, "temp")

            run_command(tutorial, "touch B\n")
            run_command(tutorial, "touch C\n")
            assert len(tutorial.undo_list) == 3
            tutorial.undo()
            assert not file_exists(tutorial, "C")
            assert len(tutorial.undo_list) == 2
            run_command(tutorial, "touch D\n")
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

            run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!")
            assert (puz1.solved, puz2.solved) == (True, False)

            tutorial.undo()
            assert not file_exists(tutorial, "B.txt")
            assert (puz1.solved, puz2.solved) == (False, False) # Puzzle is no longer solved

            run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!") # Re-solve puzzle

            run_command(tutorial, "mv C.txt D.txt\n")
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

            run_command(tutorial, "touch A\n")
            run_command(tutorial, "touch B\n")
            run_command(tutorial, "touch C\n")
            run_command(tutorial, "touch D\n")
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

            run_command(tutorial, "touch A\n")
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

            run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!")

            run_command(tutorial, "mv C.txt D.txt\n")
            assert tutorial.solve_puzzle(puz2) == (True, "Correct!")

            tutorial.restart()
            assert len(tutorial.undo_list) == 1
            assert (puz1.solved, puz2.solved) == (False, False)
            assert file_exists(tutorial, "A.txt")
            assert file_exists(tutorial, "C.txt")
