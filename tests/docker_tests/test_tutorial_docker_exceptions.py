from pathlib import PurePath
from _pytest.python_api import raises
import pytest, re
from textwrap import dedent, indent;
from shell_adventure_shared.tutorial_errors import *
from shell_adventure_shared import support
from .helpers import *

class TestTutorialDockerExceptions:
    def test_puzzle_not_found(self, working_dir):
        with pytest.raises(ConfigError, match=re.escape("Unknown puzzle template(s) 'mypuzzles.puzz_a', 'mypuzzles.puzz_b' and 'mypuzzles.puzz_c'")):
            tutorial = create_tutorial(working_dir,
                modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES},
                puzzles = ["mypuzzles.puzz_a", "mypuzzles.puzz_b", "mypuzzles.puzz_c"]
            )

    def test_config_error(self, working_dir):
        with pytest.raises(ConfigError, match="doesn't exist"):
            tutorial = create_tutorial(working_dir,
                home = "/not/a/dir",
            )

        with pytest.raises(ConfigError, match="doesn't exist"):
            tutorial = create_tutorial(working_dir,
                user = "henry",
            )


    def test_puzzle_template_bad_return(self, working_dir):
        puzzles = dedent("""
            def invalid():
                return "a string"
        """)

        with pytest.raises(UserCodeError, match="Puzzle template did not return Puzzle"):
            tutorial = create_tutorial(working_dir,
                modules = {PurePath("mypuzzles.py"): puzzles},
                puzzles = ["mypuzzles.invalid"],
            )

    def test_solve_puzzle_bad_return(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *

            def invalid():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: 100,
                )
        """)
        tutorial = create_tutorial(working_dir,
            modules = {PurePath("mypuzzles"): puzzles},
            puzzles = ["mypuzzles.invalid"],
        )
        [puzzle] = list(tutorial.puzzles.values())

        with pytest.raises(UserCodeError, match="bool or str expected"):
            tutorial.solve_puzzle(puzzle.id)

    def test_template_unrecognized_params(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *

            def puzzle(not_a_param):
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: True,
                )
        """)
        with pytest.raises(UserCodeError, match=r"Unrecognized param\(s\) 'not_a_param' in puzzle template"):
            tutorial = create_tutorial(working_dir,
                modules = {PurePath("mypuzzles.py"): puzzles},
                puzzles = ["mypuzzles.puzzle"],
            )

    def test_checker_unrecognized_params(self, working_dir):
        puzzles = dedent("""
            from shell_adventure_docker import *

            def puzzle():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda not_a_param: True,
                )
        """)

        with pytest.raises(UserCodeError, match=r"Unrecognized param\(s\) 'not_a_param' in checker function") as exc_info:
            tutorial = create_tutorial(working_dir,
                modules = {PurePath("mypuzzles.py"): puzzles},
                puzzles = ["mypuzzles.puzzle"],
            )
        assert "UnrecognizedParamsError" in str(exc_info.value)

    def test_generation_exception(self, tmp_path):
        with pytest.raises(UserCodeError, match = "Puzzle generation failed") as exc_info:
            tutorial = create_tutorial(tmp_path, 
                modules = {PurePath("puzzles.py"): dedent(r"""
                    def puzzle():
                        raise ValueError('BOOM!')
                """)},
                puzzles = ["puzzles.puzzle"],
            )

        expected = dedent("""
            Puzzle generation failed:
              Traceback (most recent call last):
                File "puzzles.py", line 3, in puzzle
                  raise ValueError('BOOM!')
              ValueError: BOOM!
        """).lstrip()
        assert expected == str(exc_info.value)

    def test_module_exception(self, tmp_path):
        with pytest.raises(UserCodeError, match = "Puzzle generation failed") as exc_info:
            tutorial = create_tutorial(tmp_path,
                modules = {PurePath("/path/to/puzzles.py"): dedent(r"""
                    1 ++
                """)},
                puzzles = ["puzzles.puzzle"],
            )

        expected = dedent("""
            Puzzle generation failed:
              Traceback (most recent call last):
                File "/path/to/puzzles.py", line 2
                  1 ++
                     ^
              SyntaxError: invalid syntax
        """).lstrip()
        assert expected == str(exc_info.value)

    def test_checker_exception(self, tmp_path):
        tutorial = create_tutorial(tmp_path, 
            modules = {PurePath("puzzles.py"): dedent(r"""
                from shell_adventure_docker import *

                def puzzle():
                    def checker():
                        raise ValueError("BOOM!")

                    return Puzzle(
                        question = f"Puzzle",
                        checker = checker,
                    )
            """)},
            puzzles = ["puzzles.puzzle"],
        )

        puz_id = list(tutorial.puzzles.keys())[0]
        with pytest.raises(UserCodeError, match = "Puzzle autograder failed") as exc_info:
            tutorial.solve_puzzle(puz_id)

        expected = dedent("""
            Puzzle autograder failed:
              Traceback (most recent call last):
                File "puzzles.py", line 6, in checker
                  raise ValueError("BOOM!")
              ValueError: BOOM!
        """).lstrip()
        assert expected == str(exc_info.value)

    def test_checker_cant_call_rand(self, tmp_path):
        tutorial = create_tutorial(tmp_path, 
            modules = {PurePath("puzzles.py"): dedent(r"""
                from shell_adventure_docker import *

                def puzzle():
                    return Puzzle(
                        question = f"Puzzle",
                        checker = lambda: rand().name(),
                    )
            """)},
            puzzles = ["puzzles.puzzle"],
        )

        puz_id = list(tutorial.puzzles.keys())[0]
        with pytest.raises(UserCodeError, match = "You can only use randomization in Puzzle templates"):
            tutorial.solve_puzzle(puz_id)

    def test_format_user_exception(self, tmp_path):
        tutorial = create_tutorial(tmp_path,
            modules = {PurePath("/path/to/puzzles.py"): dedent(r"""
                from shell_adventure_docker import *
                import lorem

                def _fails():
                    lorem.get_paragraph("a")

                def throws():
                    def checker():
                        _fails()

                    return Puzzle(
                        question = "Fails!",
                        checker = checker,
                    )
            """)},
            puzzles = ["puzzles.throws"],
        )
        [puzzle] = list(tutorial.puzzles.values())

        with pytest.raises(UserCodeError) as exc_info:
            tutorial.solve_puzzle(puzzle.id)

        # Shouldn't include our code. Should include library code.
        expected = dedent("""
          Puzzle autograder failed:
            Traceback (most recent call last):
              File "/path/to/puzzles.py", line 10, in checker
                _fails()
              File "/path/to/puzzles.py", line 6, in _fails
                lorem.get_paragraph("a")
              File "/usr/local/lib/python3.8/dist-packages/lorem.py", line 424, in get_paragraph
                return sep.join(itertools.islice(paragraph(count, comma, word_range, sentence_range), count))
            ValueError: Stop argument for islice() must be None or an integer: 0 <= x <= sys.maxsize.
        """).lstrip()
        assert expected == str(exc_info.value)

