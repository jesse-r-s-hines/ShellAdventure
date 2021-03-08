from typing import Dict
import pytest
from shell_adventure_docker.tutorial_docker import TutorialDocker
import os, subprocess
from textwrap import dedent;

# TODO use File in here.
SIMPLE_PUZZLES = dedent("""
    from os import system

    def move():
        system("echo 'move1' > A.txt")

        def checker():
            aCode = system("test -f A.txt")
            bCode = system("test -f B.txt")
            return (aCode >= 1) and (bCode == 0)

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker
        )
""")


class TestTutorialDocker:
    @staticmethod
    def _create_tutorial(tmp_path, puzzles: Dict[str, str]) -> TutorialDocker:
        """
        Creates a tutorial with the given puzzles.
        Puzzles will be saved to the dictionary key names under tmp_path/tutorial.
        Will cd into tmp_path/home
        """
        data_dir = tmp_path / "tutorial"
        data_dir.mkdir()

        (data_dir / "modules").mkdir()
        for name, content in puzzles.items():
            (data_dir / "modules" / name).write_text(content)

        working_dir = tmp_path / "home"
        working_dir.mkdir()
        os.chdir(working_dir)

        tutorial = TutorialDocker(data_dir)
        return tutorial

    def test_creation(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})

        assert set(tutorial.modules.keys()) == {"mypuzzles"}
        assert {m.__name__ for m in tutorial.modules.values()} == {"mypuzzles"}

        assert list(tutorial.generators.keys()) == ["mypuzzles.move"]
        assert tutorial.puzzles == {} # Not generated yet

    def test_str_path_creation(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})
        tutorial = TutorialDocker(f"{tmp_path / 'tutorial'}") # Strings should also work for path
        assert "mypuzzles" in tutorial.modules

    def test_multiple_modules(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {
            "mypuzzles1.py": SIMPLE_PUZZLES,
            "mypuzzles2.py": SIMPLE_PUZZLES,
        })

        assert "mypuzzles1.move" in tutorial.generators
        assert "mypuzzles2.move" in tutorial.generators

    def test_empty(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {})
        assert tutorial.modules == {}

    # TODO test module errors when I add that
    # def test_module_error(self, tmp_path):
    #     with pytest.raises():
    #         tutorial = TestTutorial._create_tutorial(tmp_path, {
    #             "bad_module.py": "syntax error!",
    #         })

    def test_generate(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})
        puzzles = tutorial.generate(["mypuzzles.move"])
        assert len(puzzles) == 1
        assert puzzles == list(tutorial.puzzles.values())
        assert puzzles[0].question == "Rename A.txt to B.txt"
        assert (tmp_path / "home" / "A.txt").exists()

    def test_generate_error(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})
        with pytest.raises(AssertionError, match="Unknown puzzle generator mypuzzles.not_a_puzzle"):
            tutorial.generate(["mypuzzles.not_a_puzzle"])
        
    def test_private_methods_arent_puzzles(self, tmp_path):
        puzzles = dedent("""
            def _private_method():
                return "not a puzzle"

            my_lambda = lambda: "not a puzzle"

            def move():
                return Puzzle(
                    question = f"Easiest puzzle ever.",
                    checker = lambda: True,
                )
        """)

        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": puzzles})
        assert list(tutorial.generators.keys()) == ["mypuzzles.move"]

    def test_solve_puzzle(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})
        [puzzle] = tutorial.generate(["mypuzzles.move"])

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        assert puzzle.solved == False

        os.system("cp A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")

        os.system("mv A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")
        assert puzzle.solved == True

    def test_solve_puzzle_bad_return(self, tmp_path):
        puzzles = dedent("""
            def invalid():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: 100,
                )
        """)
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": puzzles})
        [puzzle] = tutorial.generate(["mypuzzles.invalid"])

        with pytest.raises(Exception, match="bool or str expected"):
            tutorial.solve_puzzle(puzzle.id)

    # TODO test other puzzle errors

    def test_student_cwd(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})
        cwd = (tmp_path / "home" / "folder")
        cwd.mkdir()
        bash = subprocess.Popen("bash", stdin = subprocess.PIPE, cwd = cwd)

        try:
            tutorial.connect_to_bash()
            assert tutorial.bash_pid == bash.pid
            assert tutorial.student_cwd() == cwd
        finally:
            bash.kill()

    def test_student_cwd_spaces(self, tmp_path):
        cwd = (tmp_path / " ")
        cwd.mkdir()
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})
        bash = subprocess.Popen("bash", stdin = subprocess.PIPE, cwd = cwd)

        try:
            tutorial.connect_to_bash()
            assert tutorial.bash_pid == bash.pid
            assert tutorial.student_cwd() == cwd
        finally:
            bash.kill()

    def test_connect_to_bash_not_found(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"mypuzzles.py": SIMPLE_PUZZLES})
        with pytest.raises(ProcessLookupError):
            tutorial.connect_to_bash()

    # TODO test checker functions with different args.