from typing import List, Tuple, Dict, Any, Callable, ClassVar
from types import ModuleType
import os, json, subprocess
from multiprocessing.connection import Listener, Connection
import importlib.util, inspect
import time
from pathlib import Path;
from shell_adventure.support import Puzzle, PathLike, conn_addr, conn_key, Message
from .file import File

# TODO rename this to avoid confusion
class Tutorial:
    """ Contains the information for a running tutorial docker side. """

    _puzzle_module_inject: ClassVar[Dict[str, object]] = {
        "Puzzle": Puzzle,
    }
    """ The classes/modules/packages to inject into the puzzle generator modules. """

    data_dir: Path
    """ This is the path where tutorial files such as puzzles have been placed. """

    modules: Dict[str, ModuleType]
    """ Puzzle modules mapped to their name. """

    generators: Dict[str, Callable[[], Puzzle]]
    """ All available puzzle generator functions mapped to their name. """

    puzzles: Dict[str, Puzzle]
    """ Puzzles in this tutorial, mapped to their id. """

    def __init__(self, data_dir: PathLike):
        """
        Create a tutorial from a config_file and a PID to the bash_session the student is running.
        Any resources the config file uses should be placed in the same directory as the config file.
        """
        self.data_dir = Path(data_dir)

        # TODO test this
        # Load modules
        module_list = [self._get_module(file) for file in (self.data_dir / "modules").glob("*.py")]
        self.modules = {module.__name__: module for module in module_list}

        # Get puzzle generators from the modules
        self.generators = {}
        for module_name, module in self.modules.items():
            for func_name, func in inspect.getmembers(module, inspect.isfunction):
                # Exclude imported functions, lambdas, and private functions
                if func.__module__ == module_name and func.__name__ != "<lambda>" and not func_name.startswith("_"):
                    self.generators[f"{module_name}.{func_name}"] = func

        self.puzzles = {} # Populated when we generate the puzzles.
        self.bash_pid: int = None

    def _get_module(self, file_path: Path) -> ModuleType:
        """
        Gets a module object from a file path to the module. The file path is relative to the config file.
        Injects some functions and classes into the module's namespace. TODO doc which classes and functions
        """
        module_name = file_path.stem # strip ".py"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)

        # Inject names into the modules
        for name, obj in Tutorial._puzzle_module_inject.items():
            setattr(module, name, obj)

        spec.loader.exec_module(module) # type: ignore # MyPy is confused about the types here

        return module

    def generate(self, puzzle_generators: List[str]) -> List[Puzzle]:
        """
        Takes a list of puzzle generators and generates them. Stores the puzzles in self.puzzles.
        Returns the generated puzzles as a list.
        """
        for gen in puzzle_generators:
            # TODO Should probably raise custom exception instead of using assert (which can be removed at will)
            assert gen in self.generators, f"Unknown puzzle generator {gen}."
            puzzle = self.generators[gen]()
            self.puzzles[puzzle.id] = puzzle
            # TODO error checking

        return list(self.puzzles.values())

    def solve_puzzle(self, puzzle_id: str, flag: str = None) -> Tuple[bool, str]:
        """
        Tries to solve the puzzle with the given id.
        Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded.
        """
        puzzle = self.puzzles[puzzle_id]

        args: Dict[str, Any] = {
            # "output": output,
            # "flag": flag,
            # "file_system": self.file_system,
        }
        # Only pass the args that the checker function has
        checker_params = puzzle._get_checker_params()
        assert set(checker_params).issubset(args.keys()), 'Only paramaters, "flag", "file_system" and "output" are allowed in checker functions.'
        args = {param: args[param] for param in checker_params}

        checker_result = puzzle.checker(**args)

        if checker_result == True:
            puzzle.solved = True
            feedback = "Correct!"
        elif checker_result == False:
            feedback = "Incorrect!"
        elif isinstance(checker_result, str):
            feedback = checker_result
        else:
            raise Exception(f'Checker function for puzzle "{puzzle.question}" returned {type(checker_result).__name__}, bool or str expected.')

        return (puzzle.solved, feedback)

    def connect_to_bash(self):
        """ Finds a running bash session and stores it's id. Returns True on success. """
        pid = subprocess.check_output(["pidof", "-s", "bash"])
        self.bash_pid = None if pid.isspace() else int(pid)

        return self.bash_pid != None

    def student_cwd(self):
        """
        Return the student's current working directory. Note that in generation functions, this is different from `File.cwd()`
        File.cwd() returns the current working directory of the generation function, not the student.
        """
        if self.bash_pid == None:
            raise ProcessLookupError("No bash session specified.")
        result = subprocess.check_output(["pwdx", f"{self.bash_pid}"]) # returns "pid: /path/to/folder"
        cwd = result.decode().split(": ", 1)[1][:-1] # Split and remove trailing newline.
        return File(cwd) 

    def run(self):
        """
        Sets up a connection between the tutorial inside the docker container and the driving application outside.
        Listen for requests from the app
        """ 

        with Listener(conn_addr, authkey = conn_key) as listener:
            with listener.accept() as conn:
                actions = {
                    # Map message type to a function that will be called. The return of the lambda will be sent back to host. 
                    Message.GENERATE: lambda generators: self.generate(generators),
                    Message.CONNECT_TO_BASH: lambda: self.connect_to_bash(),
                    Message.SOLVE: lambda id: self.solve_puzzle(id),
                }

                while True: # Loop until connection ends.
                    # Messages are send as (MessageEnum, *args) tuples.
                    message, *args = conn.recv()

                    if message == Message.STOP:
                        return
                    else: # call the lambda with *args, send the return value.
                        conn.send(actions[message](*args))