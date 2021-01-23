from typing import Dict, List, Tuple, Callable, Union, ClassVar
from types import ModuleType
import os, sys, shlex
from pathlib import Path;
import docker, dockerpty
from docker.models.containers import Container
from docker.client import DockerClient
import yaml
import importlib.util, inspect

PathLike = Union[str, os.PathLike] # Type for a string representing a path or a PathLike object.

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

    def __init__(self, exit_code: int, output: str):
        self.exit_code = exit_code
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
    file_system: FileSystem
        A frozen FileSystem object. Most methods that modify the file system will be disabled.
    """
    checker: Callable[..., Union[str,bool]]

    """ Whether the puzzle is solved yet """
    solved: bool

    def __init__(self, question: str, checker: Callable[..., Union[str,bool]] , score = 1):
        self.question = question 
        self.score = score
        self.checker = checker
        self.solved = False

    def get_checker_params(self):
        return inspect.getfullargspec(self.checker).args

class FileSystem:
    """ Handles the docker container and the file system in it. """

    """ The docker daemon. """
    docker_client: DockerClient

    """ The docker container running the tutorial. """
    container: Container

    def __init__(self):
        self.docker_client = docker.from_env()
        self.container = self.docker_client.containers.run('shell-adventure',
            # Keep the container running so we can exec into it. 
            # We could run the bash session directly, but then we'd have to hide the terminal until after puzzle generation finishes.
            command = 'sleep infinity',
            tty = True,
            stdin_open = True,
            auto_remove = True,
            detach = True,
        )

    def run_command(self, command: str) -> CommandOutput:
        """ Runs the given command in the tutorial environment. Returns a tuple containing (exit_code, output). """
        exit_code, output = self.container.exec_run(shlex.join(['/bin/bash', '-c', command]))
        return CommandOutput(exit_code, output.decode())

    # TODO Move this into a context manager, or make the container run the bash command directly so that it quits when the session quits.
    def __del__(self):
        """ Stop the container. """
        if hasattr(self, "container"):
            self.container.stop(timeout = 0)

class Tutorial:
    """ Contains the information for a running tutorial. """

    """ The classes/modules/packages to inject into the puzzle generator modules. """
    _puzzle_module_inject: ClassVar[Dict[str, object]] = {
        "Puzzle": Puzzle,
    }

    """ The path to the config file for this tutorial """
    config_file: Path

    """ Puzzle modules mapped to their name. """
    modules: Dict[str, ModuleType]

    """ All available puzzle generator functions mapped to their name. """
    generators: Dict[str, Callable[[FileSystem], Puzzle]]

    class PuzzleTree:
        def __init__(self, generator: str, puzzle: Puzzle = None, dependents: List[Puzzle] = None):
            self.generator = generator; self.puzzle = puzzle
            self.dependents = dependents if dependents else None

    """ The tree of puzzles in this tutorial. """
    puzzles: List[PuzzleTree]

    """ The FileSystem object containing the Docker container for the tutorial. """
    file_system: FileSystem

    def __init__(self, config_file: PathLike):
        self.file_system = None
        self.config_file = Path(config_file)

        # TODO add validation and error checking, document config options
        with open(config_file) as temp:
            config = yaml.safe_load(temp)

            # Load modules
            files = [pkg_dir / "puzzles/default.py"] + config.get('modules', [])
            module_list = [self._get_module(Path(file)) for file in files]
            self.modules = {module.__name__: module for module in module_list}

            # Get puzzle generators from the modules
            self.generators = {}
            for module_name, module in self.modules.items():
                for func_name, func in inspect.getmembers(module, inspect.isfunction):
                    # Exclude imported functions, lambdas, and private functions 
                    if func.__module__ == module_name and func_name != "<lambda>" and not func_name.startswith("_"):
                        self.generators[f"{module_name}.{func_name}"] = func

            self.puzzles = []
            for gen in config.get('puzzles', []):
                assert gen in self.generators, f"Unknown puzzle generator {gen}."
                self.puzzles.append(Tutorial.PuzzleTree(gen))

    def _get_module(self, file_path: Path) -> ModuleType:
        """
        Gets a module object from a file path to the module. The file path is relative to the config file.
        Injects some functions and classes into the module's namespace. TODO doc which classes and functions
        """
        if (not file_path.is_absolute()): # Files are relative to the config file
            file_path = self.config_file.parent / file_path

        module_name = file_path.stem # strip ".py"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        
        # Inject names into the modules
        for name, obj in Tutorial._puzzle_module_inject.items():
            setattr(module, name, obj)

        spec.loader.exec_module(module)

        return module

    def solve_puzzle(self, puzzle: Puzzle, flag: str = None) -> Union[bool,str]:
        """ Tries to solve the puzzle. Returns the result of the checker function and sets the Puzzle as solved if the checker succeeded. """
        args = {
            # "output": output,
            "flag": flag,
            "file_system": self.file_system,
        }
        # Only pass the args that the checker function has
        checker_params = puzzle.get_checker_params()
        assert set(args.keys()).issubset(checker_params), 'Only paramaters, "flag", "filesystem" and "output" are allowed in checker functions.'
        args = {param: args[param] for param in checker_params}

        feedback = puzzle.checker(**args)

        if feedback:
            puzzle.solved = True

        return feedback

    def run(self):
        """ Starts the tutorial. """
        self.file_system = FileSystem()

        # Generate the puzzles
        for puzzle_tree in self.puzzles:
            puzzle_tree.puzzle = self.generators[puzzle_tree.generator](self.file_system)

        dockerpty.exec_command(self.file_system.docker_client.api, self.file_system.container.id, 'bash')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
    else:
        config_file = sys.argv[1]
        tutorial = Tutorial(config_file)
        tutorial.run()