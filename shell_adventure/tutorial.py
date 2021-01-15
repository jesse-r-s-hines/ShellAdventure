from typing import Dict, List, Callable, Union
from types import ModuleType
import shlex
from os import PathLike
from pathlib import Path;
import docker, dockerpty
from docker.models.containers import Container
from docker.client import DockerClient
import yaml
import importlib.util, inspect;

# Absolute path to the package folder
pkg_dir: Path = Path(__file__).parent.resolve()

class CommandOutput:
    """ Represents the output of a command. """

    """ The exit code that the command returned """
    exit_code: int
    
    """ The printed output of the command """
    output: str

    # """ Output to std error """
    # error: str

    def __init__(self, exitCode: int, output: str):
        self.exit_code = exitCode
        self.output = output

class Puzzle:
    """ Represents a single puzzle in the tutorial. """

    """ The question to be asked. """
    question: str
    
    """ The score given on success. Defaults to 1. """
    score: int

    """
    The function that will grade whether the puzzle was completed correctly or not.
    The function can take the following parameters. All parameters are optional, and order does not matter, 
    but must have the same name as listed here.
    
    output: Dict[str, CommandOutput]
        A dict of all commands entered to their outputs, in the order they were entered.
    flag: str
        If the flag parameter is present, an input dialog will be shown to the student when sumbitting a puzzle,
        and their input will be passed to this parameter.
    filesystem: FileSystem
        A frozen FileSystem object. Most methods that modify the file system will be disabled.
    """
    checker: Callable[..., Union[str,bool]] 

    def __init__(self, question: str, checker: Callable[..., Union[str,bool]] , score):
        self.question = question 
        self.score = score
        self.checker = checker

class FileSystem:
    """ Handles the docker container and the filesystem in it. """

    """ The docker daemon. """
    _client: DockerClient

    """ The docker container running the tutorial. """
    _container: Container

    def __init__(self):
        self._client = docker.from_env()
        self._container = self._client.containers.create('shell-adventure',
            command = 'tail -f /dev/null',
            tty = True,
            stdin_open = True,
            auto_remove = True,
        )

    def run_command(self, command: str) -> CommandOutput:
        """ Runs the given command in the tutorial environment. Returns a tuple containing (exit_code, output). """
        exit_code, output = self._container.exec_run(shlex.join(['/bin/bash', '-c', command]))
        return (exit_code, output.decode())

    def __del__(self):
        """ Stop the container. """
        self._container.stop(timeout = 0)

class Tutorial:
    """ Contains the information for a running tutorial. """

    config_file: str

    """ List of modules containing generator functions """
    modules: List[ModuleType]

    """ List of generator functions """
    generators: List[Callable[[FileSystem], Puzzle]]

    def __init__(self, config_file: str):
        self.config_file = config_file
        # TODO add validation and error checking, document config options
        config = yaml.safe_load(open(config_file))

        # Load modules
        files = [pkg_dir / "puzzles/default.py"] + config.get('modules', [])
        self.modules = [self._get_module(file) for file in files]

    def _get_module(self, file_path):
        """ Gets a module object from a file path to the module. The file path is relative to the config file. """
        file_path = Path(file_path)
        if (not file_path.is_absolute()): # Files are relative to the config file
            file_path = Path(self.config_file).parent / file_path

        module_name = file_path.stem # strip ".py"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # def _get_puzzle_generators(self):
    #     """ Returns the puzzle generators to run as a list of functions. """
    #     # import shell_adventure.puzzles
    #     puzzles = self.config.puzzles
    #     print(inspect.getmembers(module, inspect.isfunction))

    def start():
        """ Starts the tutorial. """


if __name__ == "__main__":
    tutorial = Tutorial(pkg_dir / "tutorials/default.yaml")
    print(tutorial.modules)