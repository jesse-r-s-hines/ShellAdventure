import pytest
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.file import File
from shell_adventure_docker.puzzle import Puzzle
import os
from textwrap import dedent;
from .helpers import *

class TestTutorialDockerSolvePuzzles:
    def test_solve_puzzle(self, working_dir):
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"]
        )
        [puzzle] = list(tutorial.puzzles.values())

        assert File("A.txt").exists()
        assert not File("B.txt").exists()

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        assert puzzle.solved == False

        os.system("cp A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")

        os.system("mv A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")
        assert puzzle.solved == True

    def test_solve_puzzle_flag(self, working_dir):
        puzzle = dedent("""
            from shell_adventure_docker import *

            def flag_puzzle():
                return Puzzle(
                    question = f"Say OK",
                    checker = lambda flag: flag == "OK",
                )
        """)
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": puzzle},
            puzzles = ["mypuzzles.flag_puzzle"],
        )
        [puzzle] = list(tutorial.puzzles.values())

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        assert tutorial.solve_puzzle(puzzle.id, "not ok") == (False, "Incorrect!")
        assert tutorial.solve_puzzle(puzzle.id, "OK") == (True, "Correct!")

    def test_solve_puzzle_twice(self, working_dir):
        module = dedent("""
            from shell_adventure_docker import *
            def puz():
                return Puzzle(question = f"Say OK", checker = lambda flag: flag == "OK")
        """)
        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": module},
            puzzles = ["mypuzzles.puz"]
        )
        [puzzle] = list(tutorial.puzzles.values())

        assert tutorial.solve_puzzle(puzzle.id, "OK") == (True, "Correct!")
        assert puzzle.solved == True

        # Solving a puzzle twice resets the solved state.
        assert tutorial.solve_puzzle(puzzle.id, "NOT OK") == (False, "Incorrect!")
        assert puzzle.solved == False
        
        assert puzzle.solved == False

    def test_puzzle_func_args(self, working_dir):
        puzzles = dedent(f"""
            from shell_adventure_docker import *

            def puzzle(home, root):
                assert home == File("{working_dir}")
                assert root == File("/")

                def checker():
                    return True

                return Puzzle(
                    question = f"Check home and root",
                    checker = checker
                )
        """)

        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": puzzles},
            puzzles = ["mypuzzles.puzzle"],
        )

    def test_checker_func_args(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *

            def puzzle(home):
                def checker(cwd):
                    return cwd == File("/home/student")

                return Puzzle( question = f"Puzzle", checker = checker )
        """)

        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": puzzles},
            puzzles = ["mypuzzles.puzzle"],
        )
        [puzzle] = list(tutorial.puzzles.values())

        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")

    def test_solve_puzzle_randomized(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *

            def move(home):
                src = home.random_file("txt")
                src.write_text(rand.paragraphs(3))
                
                dst = home.random_folder().random_file("txt") # Don't create yet

                def checker():
                    return not src.exists() and dst.exists()

                return Puzzle(
                    question = f"{src.relative_to(home)} -> {dst.relative_to(home)}",
                    checker = checker
                )
        """)

        tutorial = create_tutorial(working_dir,
            modules = {"mypuzzles": puzzles},
            puzzles = ["mypuzzles.move"],
            name_dictionary = "\n".join("abcdefg")
        )
        [puzzle] = list(tutorial.puzzles.values())

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        src, dst = map(File, puzzle.question.split(" -> "))

        os.system(f"mkdir --parents {src} {dst.parent}")
        os.system(f"mv {src} {dst}")
        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")
