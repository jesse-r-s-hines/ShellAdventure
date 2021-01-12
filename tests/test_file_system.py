import pytest
from pytest import mark
from shell_adventure.shell_adventure import *

@mark.filterwarnings("ignore:Using or importing the ABCs from")
class TestClass:

    def test_run_command(self):
        fs = FileSystem()
        fs._container.start()
  
        commands = [
            (r"echo hello world", 0, "hello world"),
            (r"echo 'hello world'", 0, "hello world"),
            (r'echo "hello world"', 0, "hello world"),
            (r'echo "\"quotes\""', 0, '"quotes"'),
            (r'echo \"quotes\"', 0, '"quotes"'),
            (r'echo "\\"', 0, "\\"), # Literal /
            (r'echo $SHELL', 0, "/bin/bash"),
            (r'pwd', 0, "/home/student"),
            (r'cd /tmp; echo "stuff" > myfile.txt', 0, ""),
            (r'pwd', 0, "/home/student"),
            (r'cd /tmp; cat myfile.txt', 0, "stuff"),
            (r'for i in {1..5}; do echo $i; done;', 0, "1\n2\n3\n4\n5"),
            (r'false', 1, ""),
        ]

        for command, expected_exit_code, expected_output in commands:
            exit_code, output = fs.run_command(command)
            assert (exit_code, output.strip()) == (expected_exit_code, expected_output), command