from typing import List, Tuple, Dict, Any, Callable, ClassVar
from types import ModuleType
import os, json, subprocess
from multiprocessing.connection import Client, Connection
import importlib.util, inspect
import time
from pathlib import Path;
from .support import Puzzle, PathLike
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

    puzzles: List[Puzzle]
    """ Puzzles in this tutorial. """

    def __init__(self, data_dir: PathLike):
        """
        Create a tutorial from a config_file and a PID to the bash_session the student is running.
        Any resources the config file uses should be placed in the same directory as the config file.
        """
        self.data_dir = Path(data_dir)
        # self.bash_pid = bash_pid # TODO add back bash stuff

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

        self.puzzles = [] # Made when we generate the puzzles.

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
        """ Takes a list of puzzle generators and generates them. Stores the puzzles. """
        for gen in puzzle_generators:
            # TODO Should probably raise custom exception instead of using assert (which can be removed at will)
            assert gen in self.generators, f"Unknown puzzle generator {gen}."
            self.puzzles.append(self.generators[gen]())
            # TODO error checking

    def solve_puzzle(self, puzzle: Puzzle, flag: str = None) -> Tuple[bool, str]:
        """ Tries to solve the puzzle. Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded. """
        args: Dict[str, Any] = {
            # "output": output,
            # "flag": flag,
            # "file_system": self.file_system,
        }
        # Only pass the args that the checker function has
        checker_params = puzzle.get_checker_params()
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

    # TODO make this work again
    # def student_cwd(self):
    #     """
    #     Return the student's current working directory. Note that in generation functions, this is different from `File.cwd()`
    #     File.cwd() returns the current working directory of the generation function, not the student.
    #     """
    #     if self.bash_pid == None:
    #         raise ProcessLookupError("No bash session specified.")
    #     result = subprocess.check_output(["pwdx", f"{self.bash_pid}"]) # returns "pid: /path/to/folder"
    #     cwd = result.decode().split(": ", 1)[1][:-1] # Split and remove trailing newline.
    #     return File(cwd) 

    def run(self):
        """
        Sets up a connection between the tutorial inside the docker container and the driving application outside.
        Listen for requests from the app
        """
        address = ('localhost', 6000) # TODO move this somewhere else so I don't have to reference it twice
        # TODO move this driving code out of Tutorial class? Rename method?

        def retry_connect(address, authkey, retries = 16, pause = 0.25):
            for attempt in range(retries - 1):
                try:
                    return Client(address, authkey=authkey)
                except ConnectionRefusedError as e:
                    time.sleep(pause)
            return Client(address, authkey=authkey) # Last time just let the error fall through.
            
        # The container can boot up before the app starts the Listener.
        with retry_connect(address, authkey = b"shell_adventure") as conn:
            puzzle_generators = conn.recv() # Get the puzzles to generate
            self.generate(puzzle_generators)

            cleaned_puzzles = [{"question": p.question, "score": p.score} for p in self.puzzles]
            conn.send(cleaned_puzzles)

            while True: # TODO add ending condition
                request = conn.recv()
                if request == "END":
                    break
                feedback = self.solve_puzzle(self.puzzles[int(request)]) # TODO handle flag
                conn.send(feedback)