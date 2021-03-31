from typing import Dict
import pytest
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.file import File
import os, subprocess
from textwrap import dedent;

# TODO use File in here.
SIMPLE_PUZZLES = dedent("""
    def move():
        file = File("A.txt")
        file.write_text("A")

        def checker():
            return not file.exists() and File("B.txt").exists()

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker
        )
""")


class TestTutorialDocker:
    @staticmethod
    def _create_tutorial(tmp_path, files: Dict[str, str]) -> TutorialDocker:
        """
        Creates a tutorial with the given files. Sets up some default files.
        Files will be saved to the dictionary key names under tmp_path/tutorial.
        Will cd into tmp_path/home and set tutorial.home to tmp_path/home
        """
        data_dir = tmp_path / "tutorial"
        data_dir.mkdir()

        default_files = {
            "name_dictionary.txt": "apple\nbanana\n"
        }
        files = {**default_files, **files} # merge

        for file, content in files.items():
            path = data_dir / file
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(content)

        working_dir = tmp_path / "home"
        working_dir.mkdir()
        os.chdir(working_dir)

        tutorial = TutorialDocker(data_dir, home = working_dir)
        return tutorial

    def test_creation(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})

        assert set(tutorial.modules.keys()) == {"mypuzzles"}
        assert {m.__name__ for m in tutorial.modules.values()} == {"mypuzzles"}

        assert list(tutorial.generators.keys()) == ["mypuzzles.move"]
        assert tutorial.puzzles == {} # Not generated yet

    def test_str_path_creation(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
        tutorial = TutorialDocker(f"{tmp_path / 'tutorial'}") # Strings should also work for path
        assert "mypuzzles" in tutorial.modules

    def test_multiple_modules(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {
            "modules/mypuzzles1.py": SIMPLE_PUZZLES,
            "modules/mypuzzles2.py": SIMPLE_PUZZLES,
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
    #             "modules/bad_module.py": "syntax error!",
    #         })

    def test_generate(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
        puzzles = tutorial.generate(["mypuzzles.move"])
        assert len(puzzles) == 1
        assert puzzles == list(tutorial.puzzles.values())
        assert puzzles[0].question == "Rename A.txt to B.txt"
        assert (tmp_path / "home" / "A.txt").exists()

    def test_generate_error(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
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

        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": puzzles})
        assert list(tutorial.generators.keys()) == ["mypuzzles.move"]

    def test_solve_puzzle(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
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
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": puzzles})
        [puzzle] = tutorial.generate(["mypuzzles.invalid"])

        with pytest.raises(Exception, match="bool or str expected"):
            tutorial.solve_puzzle(puzzle.id)

    def test_solve_puzzle_flag(self, tmp_path):
        puzzle = dedent("""
            def flag_puzzle():
                return Puzzle(
                    question = f"Say OK",
                    checker = lambda flag: flag == "OK",
                )
        """)
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": puzzle})
        [puzzle] = tutorial.generate(["mypuzzles.flag_puzzle"])

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        assert tutorial.solve_puzzle(puzzle.id, "not ok") == (False, "Incorrect!")
        assert tutorial.solve_puzzle(puzzle.id, "OK") == (True, "Correct!")

    # TODO test other puzzle errors

    def test_puzzle_func_args(self, tmp_path):
        puzzles = dedent(f"""
            def move(home, root):
                def checker():
                    return home == File("{tmp_path / 'home'}") and root == File("/")

                return Puzzle(
                    question = f"Check home and root",
                    checker = checker
                )
        """)

        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": puzzles})
        [puzzle] = tutorial.generate(["mypuzzles.move"])

        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")

    def test_solve_puzzle_randomized(self, tmp_path):
        puzzles = dedent("""
            def move():
                src = File(rand.name())
                src.write_text("stuff")
                
                dst = File(rand.name()) # Don't create yet

                def checker():
                    return not src.exists() and dst.exists()

                return Puzzle(
                    question = f"{src.name} -> {dst.name}",
                    checker = checker
                )
        """)

        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {
            "modules/mypuzzles.py": puzzles,
            "name_dictionary.txt": "apple\nbanana",
        })
        [puzzle] = tutorial.generate(["mypuzzles.move"])

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        src, dst = puzzle.question.split(" -> ")

        os.system(f"mv {src} {dst}")
        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")

    def test_student_cwd(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
        cwd = (tmp_path / "home" / "folder")
        cwd.mkdir()
        bash = subprocess.Popen("bash", stdin = subprocess.PIPE, cwd = cwd)

        try:
            tutorial.connect_to_shell("bash")
            assert tutorial.shell_pid == bash.pid
            assert tutorial.student_cwd() == cwd
        finally:
            bash.kill()

    def test_student_cwd_spaces(self, tmp_path):
        cwd = (tmp_path / " ")
        cwd.mkdir()
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
        bash = subprocess.Popen("bash", stdin = subprocess.PIPE, cwd = cwd)

        try:
            tutorial.connect_to_shell("bash")
            assert tutorial.shell_pid == bash.pid
            assert tutorial.student_cwd() == cwd
        finally:
            bash.kill()

    def test_connect_to_shell_not_found(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
        with pytest.raises(ProcessLookupError, match = "No process"):
            tutorial.connect_to_shell("bash")

    def test_connect_to_shell_multiple_found(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
        bash1 = subprocess.Popen("bash", stdin = subprocess.PIPE)
        bash2 = subprocess.Popen("bash", stdin = subprocess.PIPE)

        with pytest.raises(ProcessLookupError, match = "Multiple processes"):
            tutorial.connect_to_shell("bash")

    def test_get_files(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})

        a = File("A"); a.mkdir()
        File("A/B").create()
        File("C").create()
        File("D").symlink_to(a)

        files = tutorial.get_files(tmp_path / "home")
        assert all([f.is_absolute() for _, _, f in files])
        home = tmp_path / "home"
        assert set(files) == {(True, False, home / "A"), (False, False, home / "C"), (True, True, home / "D")}

    def test_get_special_files(self, tmp_path):
        tutorial = TestTutorialDocker._create_tutorial(tmp_path, {"modules/mypuzzles.py": SIMPLE_PUZZLES})
        
        def get_files_recursive(folder):
            all_files = []
            for is_dir, is_symlink, file in tutorial.get_files(folder):
                all_files.append(file)
                if is_dir and not is_symlink:
                    all_files.extend(get_files_recursive(file))
            return all_files

        # /proc has special files that sometimes throws errors when trying to get them via python. Test that they are handled properly.
        assert get_files_recursive("/proc") != []