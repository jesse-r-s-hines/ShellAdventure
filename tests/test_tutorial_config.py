from typing import *
import pytest
from shell_adventure.host_side.tutorial import Tutorial
from textwrap import dedent;
from pathlib import Path
import re, sys
from .helpers import *
from shell_adventure.shared.tutorial_errors import *

class TestTutorialConfig:
    def test_simple_tutorial(self, tmp_path: Path, check_containers):
        # Create the files
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": SIMPLE_TUTORIAL,
            "mypuzzles.py": SIMPLE_PUZZLES,
        })
        tutorial = Tutorial(f"{tmp_path / 'config.yaml'}") # Strings should also work for path
        assert tutorial.config_file == tmp_path / "config.yaml"
        assert tutorial.name_dictionary.name == "name_dictionary.txt"

    def test_creation(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": f"""
                image: my-custom-image:latest
                container_options:
                    working_dir: /home/user
                    user: user
                    command: sh
                    name: mytutorial
                setup_scripts:
                    - setup.py
                modules:
                    - path/to/puzz1.py # Relative path
                    - {tmp_path / "puzz2.py"} # Absolute path
                    - path/../puzz3.py # path with ".."
                puzzles:
                    - puzz1.move
                    - puzz2.move
                    - puzz3.move
                name_dictionary: "my_dictionary.txt"
                content_sources:
                    - content.txt
            """,
            "setup.py": "File('A.txt').create()",
            "path/to/puzz1.py": SIMPLE_PUZZLES,
            "puzz2.py": SIMPLE_PUZZLES,
            "puzz3.py": SIMPLE_PUZZLES,
            "my_dictionary.txt": "a\nb\nc\n",
            "content.txt": "STUFF\n\nSTUFF\n\nMORE STUFF\n",
        })
        assert tutorial.data_dir == tmp_path
        assert tutorial.image == "my-custom-image:latest"
        assert tutorial.container_options == {
            "working_dir": "/home/user",
            "user": "user",
            "command": "sh",
            "name": "mytutorial",
        }
        assert tutorial.name_dictionary == tmp_path / "my_dictionary.txt"
        assert tutorial.content_sources == [tmp_path / "content.txt"]

        assert [s for s in tutorial.setup_scripts] == [tmp_path / "setup.py"]
        assert [m for m in tutorial.module_paths] == [tmp_path / "path/to/puzz1.py", tmp_path / "puzz2.py", tmp_path / "puzz3.py"]
        assert [n.data for n in tutorial.puzzle_templates] == ["puzz1.move", "puzz2.move", "puzz3.move"]

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
        # First level
        assert [n.data for n in tutorial.puzzle_templates] == ["puzz1.move", "puzz4.move", "puzz5.move"]

        # Second Level
        assert [n.data for n in tutorial.puzzle_templates[0].children] == ["puzz2.move"]
        assert [n.data for n in tutorial.puzzle_templates[2].children] == ["puzz6.move"]

        # Third Level
        assert [n.data for n in tutorial.puzzle_templates[0][0].children] == ["puzz3.move"]

    def test_missing_files(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError, match = r"No such file or directory.*not_a_config_file\.yaml"):
            tutorial = Tutorial(tmp_path / "not_a_config_file.yaml")

        tutorial = create_tutorial(tmp_path, {"config.yaml": SIMPLE_TUTORIAL}) # Don't make any puzzle files
        with pytest.raises(ConfigError, match = r"No such file or directory.*puzzles\.py"):
            with tutorial: pass # We have to try and launch the tutorial before modules are opened

        tutorial = create_tutorial(tmp_path, {
            "config.yaml": SIMPLE_TUTORIAL,
            "mypuzzles.py/file": "", # make mypuzzles.py a directory
        })
        with pytest.raises(ConfigError, match = r".*puzzles\.py"):
            with tutorial: pass

    def test_duplicate_module_names(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError, match='Multiple puzzle modules with name "puzzle1" found'):
            tutorial = create_tutorial(tmp_path, {
                "config.yaml": """
                    modules:
                        - puzzle1.py
                        - path/to/puzzle1.py
                    puzzles:
                        - puzzle1.move
                """,
                "puzzle1.py": SIMPLE_PUZZLES,
                "path/to/puzzle1.py": SIMPLE_PUZZLES,
            })

    def test_validation_error(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError) as exc_info:
            tutorial = create_tutorial(tmp_path, {
                "config.yaml": """
                    restart_enabled: 20
                    puzzles:
                        puzzles.move:
                """,
                "puzzles.py": SIMPLE_PUZZLES,
            })
        message = str(exc_info.value)

        assert re.search('Validation error in ".*config.yaml"', message)
        assert re.search("restart_enabled: .* is not a bool.", message)
        assert re.search("modules: Required field missing", message)
        assert re.search("puzzles: .* is not a list.", message)

    def test_validation_error_puzzles(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError, match = "Length of .* is greater than 1"):
            tutorial = create_tutorial(tmp_path, {
                "config.yaml": f"""
                    modules:
                        - puzzles.py
                    puzzles:
                        - puzzles.move:
                          puzzles.move2:
                """,
                "puzzles.py": SIMPLE_PUZZLES,
            })

    def test_validation_error_puzzles_bad_format(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError) as exc_info:
            tutorial = create_tutorial(tmp_path, {
                "config.yaml": f"""
                    modules:
                        - puzzles.py
                    puzzles:
                        - move
                        - 1ab.1ab
                        - à.ñ # python allows unicode identifiers
                """,
                "puzzles.py": SIMPLE_PUZZLES,
            })
        message = str(exc_info.value)

        assert "'move' is not a python identifier of format 'module.puzzle'" in message
        assert "'1ab.1ab' is not a python identifier of format 'module.puzzle'" in message
        assert "à.ñ" not in message # unicode is valid

    def test_config_parse_error(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError):
            tutorial = create_tutorial(tmp_path, {
                "config.yaml": """
                    modules: - -
                """,
                "puzzles.py": SIMPLE_PUZZLES,
            })

    def test_empty_config(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError):
            tutorial = create_tutorial(tmp_path, {"config.yaml": "", "mypuzzles.py": SIMPLE_PUZZLES})

    def test_container_options_command_list(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": f"""
                container_options:
                    command: ["sh", "-i"]
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        assert tutorial.container_options["command"] == ["sh", "-i"]

    def test_container_options_unrecognized_keys(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": f"""
                container_options:
                    1: 1 # Not a string key
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        with pytest.raises(ContainerStartupError, match = "unexpected keyword argument '1'"):
            with tutorial: pass

    def test_container_options_wrong_type(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError, match = "'1' is not a str"):
            tutorial = create_tutorial(tmp_path, {
                "config.yaml": f"""
                    container_options:
                        command: ["sh", 1]
                    modules:
                        - puzzles.py
                    puzzles:
                        - puzzles.move
                """,
                "puzzles.py": SIMPLE_PUZZLES,
            })

    @pytest.mark.skipif(sys.platform == "win32", reason = "Malformed Docker API calls hang on Windows")
    def test_container_options_api_error(self, tmp_path: Path, check_containers):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": f"""
                container_options:
                    labels: 1 # Not string
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        # Will just print the API error since docker-py doesn't seem to type check the command
        with pytest.raises(ContainerStartupError) as exc_info:
            with tutorial: pass

        if sys.platform.startswith("linux"): # Only Linux gives any useful error message back
            assert re.search("labels", str(exc_info.value), re.IGNORECASE)

    def test_empty_fields(self, tmp_path: Path, check_containers):
        with pytest.raises(ConfigError) as exc_info:
            tutorial = create_tutorial(tmp_path, {
                "config.yaml": f"""
                    image:
                    container_options:
                    show_tree: null
                    modules:
                        - puzzles.py
                    puzzles:
                        - puzzles.move
                """,
                "puzzles.py": SIMPLE_PUZZLES,
            })

        message = str(exc_info.value)
        assert "image: 'None' is not a str" in message
        assert "container_options : 'None' is not a map" in message
        assert "show_tree: 'None' is not a bool" in message