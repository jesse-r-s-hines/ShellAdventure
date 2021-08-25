from pathlib import PurePath, Path
import pytest, re
from textwrap import dedent, indent;
from shell_adventure.shared.tutorial_errors import *
from shell_adventure.docker_side.tutorial_docker import TutorialDocker
from .helpers import *

class TestTutorialDockerExceptions:
    def test_puzzle_not_found(self, working_dir: Path):
        with pytest.raises(ConfigError, match=re.escape("Unknown puzzle template(s) 'mypuzzles.puzz_a', 'mypuzzles.puzz_b' and 'mypuzzles.puzz_c'")):
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    modules = {PurePath("mypuzzles.py"): SIMPLE_PUZZLES},
                    puzzles = ["mypuzzles.puzz_a", "mypuzzles.puzz_b", "mypuzzles.puzz_c"]
                )

    def test_config_error(self, working_dir: Path):
        with pytest.raises(ConfigError, match="doesn't exist"):
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    home = "/not/a/dir",
                )

        with pytest.raises(ConfigError, match="doesn't exist"):
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    user = "henry",
                )


    def test_puzzle_template_bad_return(self, working_dir: Path):
        puzzles = dedent("""
            def invalid():
                return "a string"
        """)

        with pytest.raises(UserCodeError, match="Puzzle template mypuzzles.invalid did not return a Puzzle"):
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    modules = {PurePath("mypuzzles.py"): puzzles},
                    puzzles = ["mypuzzles.invalid"],
                )

    def test_solve_puzzle_bad_return(self, working_dir: Path):
        puzzles = dedent("""
            from shell_adventure.api import *

            def invalid():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: 100,
                )
        """)
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {PurePath("mypuzzles"): puzzles},
                puzzles = ["mypuzzles.invalid"],
            )
            [puzzle] = list(tutorial.puzzles.values())

            with pytest.raises(UserCodeError, match="mypuzzles.invalid returned int, expected bool or str"):
                tutorial.solve_puzzle(puzzle.id)

    def test_template_unrecognized_params(self, working_dir: Path):
        puzzles = dedent("""
            from shell_adventure.api import *

            def puzzle(not_a_param):
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda: True,
                )
        """)
        with pytest.raises(UserCodeError,
            match = r"Unrecognized param\(s\) 'not_a_param' in puzzle template mypuzzles.puzzle"
        ):
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    modules = {PurePath("mypuzzles.py"): puzzles},
                    puzzles = ["mypuzzles.puzzle"],
                )

    def test_checker_unrecognized_params(self, working_dir: Path):
        puzzles = dedent("""
            from shell_adventure.api import *

            def puzzle():
                return Puzzle(
                    question = f"This puzzle is invalid",
                    checker = lambda not_a_param: True,
                )
        """)

        with pytest.raises(UserCodeError, match=r"Unrecognized param\(s\) 'not_a_param' in checker function") as exc_info:
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    modules = {PurePath("mypuzzles.py"): puzzles},
                    puzzles = ["mypuzzles.puzzle"],
                )
        assert "UnrecognizedParamsError" in str(exc_info.value)

    def test_setup_script_exception(self, working_dir: Path):
        with pytest.raises(UserCodeError, match='Setup scripts failed') as exc_info:
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    setup_scripts = {PurePath("script.py"): r"""raise TypeError('BOOM!')"""}
                )

        expected = dedent("""
            Setup scripts failed:
              Traceback (most recent call last):
                File "script.py", line 1, in <module>
                  raise TypeError('BOOM!')
              TypeError: BOOM!
        """).lstrip()
        assert expected == str(exc_info.value)


    def test_generation_exception(self, working_dir: Path):
        with pytest.raises(UserCodeError, match = "Puzzle generation failed") as exc_info:
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    modules = {PurePath("puzzles.py"): dedent(r"""
                        def puzzle():
                            raise ValueError('BOOM!')
                    """)},
                    puzzles = ["puzzles.puzzle"],
                )

        expected = dedent("""
            Puzzle generation failed for template puzzles.puzzle:
              Traceback (most recent call last):
                File "puzzles.py", line 3, in puzzle
                  raise ValueError('BOOM!')
              ValueError: BOOM!
        """).lstrip()
        assert expected == str(exc_info.value)

    def test_module_exception(self, working_dir: Path):
        with pytest.raises(UserCodeError, match = "Puzzle generation failed") as exc_info:
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
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

    def test_checker_exception(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
            modules = {PurePath("puzzles.py"): dedent(r"""
                    from shell_adventure.api import *

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
            with pytest.raises(UserCodeError, match = "Puzzle autograder .* failed") as exc_info:
                tutorial.solve_puzzle(puz_id)

        expected = dedent("""
            Puzzle autograder for template puzzles.puzzle failed:
              Traceback (most recent call last):
                File "puzzles.py", line 6, in checker
                  raise ValueError("BOOM!")
              ValueError: BOOM!
        """).lstrip()
        assert expected == str(exc_info.value)

    def test_checker_cant_call_rand(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {PurePath("puzzles.py"): dedent(r"""
                    from shell_adventure.api import *

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

    def test_format_user_exception(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {PurePath("/path/to/puzzles.py"): dedent(r"""
                    from shell_adventure.api import *
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
          Puzzle autograder for template puzzles.throws failed:
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

    def test_format_user_exception_with_colon_filename(self, working_dir: Path):
        with TutorialDocker() as tutorial:
            setup_tutorial(tutorial, working_dir,
                modules = {PurePath("/path:with/colon/puzzles.py"): dedent(r"""
                    from shell_adventure.api import *

                    def throws():
                        def checker(): raise Exception("BOOM!")
                        return Puzzle(question = "Fails!", checker = checker)
                """)},
                puzzles = ["puzzles.throws"],
            )
            [puzzle] = list(tutorial.puzzles.values())

            with pytest.raises(UserCodeError) as exc_info:
                tutorial.solve_puzzle(puzzle.id)

        # Shouldn't include our code. Should include library code.
        expected = dedent("""
          Puzzle autograder for template puzzles.throws failed:
            Traceback (most recent call last):
              File "/path:with/colon/puzzles.py", line 5, in checker
                def checker(): raise Exception("BOOM!")
            Exception: BOOM!
        """).lstrip()
        assert expected == str(exc_info.value)


    def test_unpickleable_checker(self, working_dir: Path):
        with pytest.raises(UserCodeError, match = "Unpickleable autograder function in 'puzzles.unpickleable'") as exc_info:
            with TutorialDocker() as tutorial:
                setup_tutorial(tutorial, working_dir,
                    modules = {PurePath("puzzles.py"): dedent(r"""
                        from shell_adventure.api import *

                        def unpickleable():
                            gen = (i for i in range(1, 10))
                            return Puzzle(
                                question = f"Unpickleable",
                                checker = lambda: gen != None,
                            )
                    """)},
                    puzzles = ["puzzles.unpickleable"],
                    send_checkers = True,
                )

        assert re.search("TypeError: cannot pickle 'generator' object", str(exc_info.value))