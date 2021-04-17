import pytest
import shell_adventure_docker
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.file import File
from shell_adventure.support import ScriptType
import os, subprocess
from textwrap import dedent;

SIMPLE_PUZZLES = dedent("""
    from shell_adventure_docker import *

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
    def _create_tutorial(working_dir, **setup) -> TutorialDocker:
        """
        Factory for TutorialDocker. Pass args that will be passed to setup().
        Provides some default for setup() args
        tutorial.home to working_dir
        """
        default_setup = {
            "home": working_dir,
            "setup_scripts": [],
            "modules": {"puzzles": SIMPLE_PUZZLES},
            "puzzles": ["puzzles.move"],
            "name_dictionary": "apple\nbanana\n",
            "content_sources": [],
        }
        setup = {**default_setup, **setup} # merge

        tutorial = TutorialDocker()
        tutorial.setup(**setup)

        return tutorial

    def test_creation(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir,
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"],
        )

        assert shell_adventure_docker.rand != None # _random should be set

        assert set(tutorial.modules.keys()) == {"mypuzzles"}
        assert {m.__name__ for m in tutorial.modules.values()} == {"mypuzzles"}

        assert list(tutorial.generators.keys()) == ["mypuzzles.move"]

        [puzzle] = list(tutorial.puzzles.values())
        assert puzzle.question == "Rename A.txt to B.txt"
        assert (working_dir / "A.txt").exists()


    def test_multiple_modules(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir,
            modules = {
                "mypuzzles1": SIMPLE_PUZZLES,
                "mypuzzles2": SIMPLE_PUZZLES,
            },
            puzzles = ["mypuzzles1.move", "mypuzzles2.move"],
        )

        assert "mypuzzles1.move" in tutorial.generators
        assert "mypuzzles2.move" in tutorial.generators
        assert len(tutorial.puzzles) == 2

    def test_empty(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir, modules = {}, puzzles = [])
        assert tutorial.modules == {}
        assert tutorial.puzzles == {}

    # TODO test module errors when I add that
    # def test_module_error(self, working_dir):
    #     with pytest.raises():
    #         tutorial = TestTutorial._create_tutorial(working_dir, modules = {
    #             "bad_module": "syntax error!",
    #         })

    def test_generate_error(self, working_dir):
        with pytest.raises(Exception, match="Unknown puzzle generator mypuzzles.not_a_puzzle"):
            tutorial = TestTutorialDocker._create_tutorial(working_dir,
                modules = {"mypuzzles": SIMPLE_PUZZLES},
                puzzles = ["mypuzzles.not_a_puzzle"]
            )
        
    def test_private_methods_arent_puzzles(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *
            from os import system # Don't use the imported method as a puzzle.

            def _private_method():
                return "not a puzzle"

            my_lambda = lambda: "not a puzzle"

            def move():
                return Puzzle(
                    question = f"Easiest puzzle ever.",
                    checker = lambda: True,
                )
        """)

        tutorial = TestTutorialDocker._create_tutorial(working_dir, modules = {"mypuzzles": puzzles}, puzzles = [])
        assert list(tutorial.generators.keys()) == ["mypuzzles.move"]

    def test_solve_puzzle(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir,
            modules = {"mypuzzles": SIMPLE_PUZZLES},
            puzzles = ["mypuzzles.move"]
        )
        [puzzle] = list(tutorial.puzzles.values())

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        assert puzzle.solved == False

        os.system("cp A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")

        os.system("mv A.txt B.txt")
        assert tutorial.solve_puzzle(puzzle.id) == (True, "Correct!")
        assert puzzle.solved == True

    def test_solve_puzzle_bad_return(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *

            def invalid():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: 100,
                )
        """)
        tutorial = TestTutorialDocker._create_tutorial(working_dir,
            modules = {"mypuzzles": puzzles},
            puzzles = ["mypuzzles.invalid"],
        )
        [puzzle] = list(tutorial.puzzles.values())

        with pytest.raises(Exception, match="bool or str expected"):
            tutorial.solve_puzzle(puzzle.id)

    def test_solve_puzzle_flag(self, working_dir):
        puzzle = dedent("""
            from shell_adventure_docker import *

            def flag_puzzle():
                return Puzzle(
                    question = f"Say OK",
                    checker = lambda flag: flag == "OK",
                )
        """)
        tutorial = TestTutorialDocker._create_tutorial(working_dir,
            modules = {"mypuzzles": puzzle},
            puzzles = ["mypuzzles.flag_puzzle"],
        )
        [puzzle] = list(tutorial.puzzles.values())

        assert tutorial.solve_puzzle(puzzle.id) == (False, "Incorrect!")
        assert tutorial.solve_puzzle(puzzle.id, "not ok") == (False, "Incorrect!")
        assert tutorial.solve_puzzle(puzzle.id, "OK") == (True, "Correct!")

    # TODO test other puzzle errors

    def test_puzzle_func_args(self, working_dir):
        puzzles = dedent(f"""
            from shell_adventure_docker import *

            def move(home, root):
                def checker():
                    return home == File("{working_dir}") and root == File("/")

                return Puzzle(
                    question = f"Check home and root",
                    checker = checker
                )
        """)

        tutorial = TestTutorialDocker._create_tutorial(working_dir,
            modules = {"mypuzzles": puzzles},
            puzzles = ["mypuzzles.move"],
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

        tutorial = TestTutorialDocker._create_tutorial(working_dir,
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

    def test_student_cwd(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir)
        cwd = (working_dir / "folder")
        cwd.mkdir()
        bash = subprocess.Popen("bash", stdin = subprocess.PIPE, cwd = cwd)

        try:
            tutorial.connect_to_shell("bash")
            assert tutorial.shell_pid == bash.pid
            assert tutorial.student_cwd() == cwd
        finally:
            bash.kill()

    def test_student_cwd_spaces(self, working_dir):
        cwd = (working_dir / " ")
        cwd.mkdir()
        tutorial = TestTutorialDocker._create_tutorial(working_dir)
        bash = subprocess.Popen("bash", stdin = subprocess.PIPE, cwd = cwd)

        try:
            tutorial.connect_to_shell("bash")
            assert tutorial.shell_pid == bash.pid
            assert tutorial.student_cwd() == cwd
        finally:
            bash.kill()

    # def test_connect_to_shell_not_found(self, working_dir):
    #     tutorial = TestTutorialDocker._create_tutorial(working_dir)
    #     with pytest.raises(ProcessLookupError, match = "No process"):
    #         tutorial.connect_to_shell("bash")

    # def test_connect_to_shell_multiple_found(self, working_dir):
    #     tutorial = TestTutorialDocker._create_tutorial(working_dir)
    #     bash1 = subprocess.Popen("bash", stdin = subprocess.PIPE)
    #     bash2 = subprocess.Popen("bash", stdin = subprocess.PIPE)

    #     with pytest.raises(ProcessLookupError, match = "Multiple processes"):
    #         tutorial.connect_to_shell("bash")

    def test_get_files(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir, puzzles = [])

        a = File("A"); a.mkdir()
        File("A/B").create()
        File("C").create()
        File("D").symlink_to(a)

        files = tutorial.get_files(working_dir)
        assert all([f.is_absolute() for _, _, f in files])
        assert set(files) == {(True, False, working_dir / "A"), (False, False, working_dir / "C"), (True, True, working_dir / "D")}

    def test_get_special_files(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir)
        
        def get_files_recursive(folder):
            all_files = []
            for is_dir, is_symlink, file in tutorial.get_files(folder):
                all_files.append(file)
                if is_dir and not is_symlink:
                    all_files.extend(get_files_recursive(file))
            return all_files

        # /proc has special files that sometimes throws errors when trying to get them via python. Test that they are handled properly.
        assert get_files_recursive("/proc") != []


    def test_setup_scripts(self, working_dir):
        tutorial = TestTutorialDocker._create_tutorial(working_dir,
            modules = {"mypuzzles": dedent(r"""
                from shell_adventure_docker import *

                def puzzle():
                    output = File("output.txt")
                    output.write_text(output.read_text() + "generator\n")

                    return Puzzle(
                        question = f"WRONG",
                        checker = lambda: False,
                    )
            """)},
            puzzles = ["mypuzzles.puzzle"],
            setup_scripts = [
                (ScriptType.BASH, dedent(r"""
                    echo \"$SHELL\" > output.txt
                """)),
                (ScriptType.PYTHON, dedent(r"""
                    from shell_adventure_docker import *

                    rand.paragraphs(3) # check that this is not null
                    output = File("output.txt")
                    output.write_text(output.read_text() + "python\n")
                """)),
            ]
        )

        output = working_dir / "output.txt"
        assert output.read_text().splitlines() == ['"/bin/bash"', 'python', 'generator']
        assert (output.owner(), output.group()) == ("root", "root")
