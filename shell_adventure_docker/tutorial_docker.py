from typing import List, Tuple, Dict, Any, Callable, ClassVar
from types import ModuleType
from pathlib import Path, PurePosixPath;
import subprocess
from multiprocessing.connection import Listener
import importlib.util, inspect
from retry.api import retry_call
from shell_adventure import support
from shell_adventure.support import Puzzle, PathLike, Message
from .file import File
from .permissions import change_user

class TutorialDocker:
    """ Contains the information for a running tutorial docker side. """

    _puzzle_module_inject: ClassVar[Dict[str, object]] = {
        "Puzzle": Puzzle,
        "File": File,
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
        for name, obj in TutorialDocker._puzzle_module_inject.items():
            setattr(module, name, obj)

        spec.loader.exec_module(module) # type: ignore # MyPy is confused about the types here

        return module

    ### Message actions, these functions can be called by sending a message over the connection

    def generate(self, puzzle_generators: List[str]) -> List[Puzzle]:
        """
        Takes a list of puzzle generators and generates them. Stores the puzzles in self.puzzles.
        Returns the generated puzzles as a list.
        """
        args = { # TODO add documentation for args you can take in generator function
            "home": File("/home/student"), # can't use home() since the user is actually root. #TODO add docs that File.home() doesn't work as expected. 
            "root": File("/"),
        }

        for gen in puzzle_generators:
            # TODO Should probably raise custom exception instead of using assert (which can be removed at will)
            assert gen in self.generators, f"Unknown puzzle generator {gen}."
            puzzle: Puzzle = support.call_with_args(self.generators[gen], args)
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
            "cwd": self.student_cwd(),
        }
        checker_result = support.call_with_args(puzzle.checker, args)

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

    def connect_to_bash(self) -> int:
        """ Finds a running bash session and stores it's id. Returns the pid. """
        try:
            # retry a few times since exec'ing into the container can take a bit.
            result = retry_call(lambda: subprocess.check_output(["pidof", "-s", "bash"]), tries=20, delay=0.1)
            self.bash_pid = int(result)
        except subprocess.CalledProcessError:
            raise ProcessLookupError("No bash session to connect to.")
        return self.bash_pid

    def get_files(self, folder: PurePosixPath) -> List[Tuple[bool, bool, PurePosixPath]]:
        """
        Returns a list of files under the given folder as a list of (is_dir, is_symlink, path) tuples.
        folder should be an absolute path.
        """
        real_folder = Path(folder) # convert to real PosixPath
        assert real_folder.is_absolute()
        # Convert to PurePosixPath since we are going to send it over to a system that may be Windows. And the file doesn't exist on host.
        with change_user("root"): # Access all files
            return [(f.is_dir(), f.is_symlink(), PurePosixPath(f)) for f in real_folder.iterdir()]

    ### Other methods

    def student_cwd(self):
        """
        Return the student's current working directory. Note that in generation functions, this is different from `File.cwd()`
        File.cwd() returns the current working directory of the generation function, not the student.
        Returns None if bash_pid is not set.
        """
        if self.bash_pid == None:
            return None
        with change_user("root"):
            result = subprocess.check_output(["pwdx", f"{self.bash_pid}"]) # returns "pid: /path/to/folder"
        cwd = result.decode().split(": ", 1)[1][:-1] # Split and remove trailing newline.
        return File(cwd) 

    def run(self):
        """
        Sets up a connection between the tutorial inside the docker container and the driving application outside.
        Listen for requests from the app
        """ 

        with Listener(support.conn_addr, authkey = support.conn_key) as listener:
            with listener.accept() as conn:
                actions = {
                    # Map message type to a function that will be called. The return of the lambda will be sent back to host. 
                    Message.GENERATE: self.generate,
                    Message.CONNECT_TO_BASH: self.connect_to_bash,
                    Message.SOLVE: self.solve_puzzle,
                    Message.GET_FILES: self.get_files,
                }

                while True: # Loop until connection ends.
                    # Messages are send as (MessageEnum, *args) tuples.
                    message, *args = conn.recv()

                    if message == Message.STOP:
                        return
                    else: # call the lambda with *args, send the return value.
                        conn.send(actions[message](*args))