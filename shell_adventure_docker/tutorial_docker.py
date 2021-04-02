from typing import List, Tuple, Dict, Any, Callable, ClassVar
from types import ModuleType
from pathlib import Path, PurePosixPath;
import subprocess, os
from multiprocessing.connection import Listener
import inspect
from retry.api import retry_call
from shell_adventure import support
from shell_adventure.support import Puzzle, PathLike, Message
from .file import File
from .permissions import change_user
from .random_helper import RandomHelper

class TutorialDocker:
    """ Contains the information for a running tutorial docker side. """

    home: Path
    """ This is the folder that puzzle generators and checkers will be run in. Defaults to /home/student but can be changed for testing purposes. """

    modules: Dict[str, ModuleType]
    """ Puzzle modules mapped to their name. """

    generators: Dict[str, Callable[[], Puzzle]]
    """ All available puzzle generator functions mapped to their name. """

    puzzles: Dict[str, Puzzle]
    """ Puzzles in this tutorial, mapped to their id. """

    random: RandomHelper
    """ An instance of RandomHelper which will generate random names and such. """

    shell_pid: int
    """ The pid of the shell session the tutorial is connected to. """

    def __init__(self):
        """ Create a tutorial. You need to call setup() afterwards to actually set and generate the puzzles etc. """
        # We don't really do anything in here, the tutorial is initialized in the "setup" method when we are actually sent the settings.
        self.home = None
        self.random = None
        self.modules = []
        self.generators = {}
        self.puzzles = {}
        self.shell_pid: int = None

    def _create_module(self, name: str, code: str) -> ModuleType:
        """
        Constructs a module object from a string of python code.
        Injects some functions and classes into the module's namespace. TODO doc which classes and functions
        """
        module = ModuleType(name)
        module.__dict__.update({ # The classes/modules/packages to inject into the modules.
            "Puzzle": Puzzle,
            "File": File,
            "rand": self.random
        })
        exec(code, module.__dict__) # Uses funcs as globals.
        return module

    def _get_generators(self, module: ModuleType):
        """ Extracts puzzle generator functions from a module as a map of {name: func} """
        generators = {}
        for func_name, func in inspect.getmembers(module, inspect.isfunction):
            # Exclude imported functions, lambdas, and private functions
            if func.__module__ == module.__name__ and func.__name__ != "<lambda>" and not func_name.startswith("_"):
                generators[f"{module.__name__}.{func_name}"] = func

        return generators

    def _generate_puzzle(self, puzzle_generator: str) -> Puzzle:
        """   Takes a puzzle generators and generates a puzzle from it. """
        # TODO custom exception 
        if puzzle_generator not in self.generators: raise Exception(f"Unknown puzzle generator {puzzle_generator}.")

        args = { # TODO add documentation for args you can take in generator function
            "home": File(self.home), # can't use home() since the user is actually root. #TODO add docs that File.home() doesn't work as expected. 
            "root": File("/"),
        }

        os.chdir(self.home) # Make sure generators are called with home as the cwd
        puzzle: Puzzle = support.call_with_args(self.generators[puzzle_generator], args)
        # TODO error checking

        return puzzle

    ### Message actions, these functions can be called by sending a message over the connection
    
    def setup(self, home: PathLike, modules: Dict[str, str], puzzles: List[str],
              name_dictionary: str, content_sources: List[str]) -> List[Puzzle]:
        """
        Initializes the tutorial with the given settings. Generates the puzzles in the modules.
        The initialization is done separate from the constructor so that it can be done after the connection with the host is setup.
        Returns the generated puzzles as a list.
        """
        self.home = Path(home)
        self.random = RandomHelper(name_dictionary, content_sources)
        # Unfortunately we have to have a static variable in File to allow File methods to access the RandomHelper
        File._random = self.random 

        # Load modules
        self.modules = {name: self._create_module(name, code) for name, code in modules.items()}

        # Get puzzle generators from the modules
        self.generators = {}
        for module in self.modules.values(): 
            self.generators.update( self._get_generators(module) )

        puzzle_list = [self._generate_puzzle(gen) for gen in puzzles]
        self.puzzles = {p.id: p for p in puzzle_list}

        self.shell_pid: int = None

        return puzzle_list

    def solve_puzzle(self, puzzle_id: str, flag: str = None) -> Tuple[bool, str]:
        """
        Tries to solve the puzzle with the given id.
        Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded.
        """
        puzzle = self.puzzles[puzzle_id]

        os.chdir(self.home) # Make sure each puzzle is called with home as its current directory
        args: Dict[str, Any] = {
            # "output": output,
            "flag": flag,
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

    def connect_to_shell(self, name: str) -> int:
        """ Finds a running shell session with the given name and stores it's pid. Returns the pid. """
        try:
            # retry a few times since exec'ing into the container can take a bit, or something else may have spun up its own temporary bash session
            self.shell_pid = retry_call(lambda: int(subprocess.check_output(["pidof", name])), tries=40, delay=0.2) # type: ignore
        except subprocess.CalledProcessError:
            raise ProcessLookupError(f'No process named "{name}" found.')
        except ValueError: # int parse fails because more than one pid was returned
            raise ProcessLookupError(f'Multiple processes named "{name}" found.')

        return self.shell_pid

    def get_files(self, folder: PathLike) -> List[Tuple[bool, bool, PurePosixPath]]:
        """
        Returns a list of files under the given folder as a list of (is_dir, is_symlink, path) tuples.
        folder should be an absolute path.
        """
        real_folder = Path(folder) # convert to real PosixPath
        assert real_folder.is_absolute()
        # Convert to PurePosixPath since we are going to send it over to a system that may be Windows. And the file doesn't exist on host.
        with change_user("root"): # Access all files
            try:
                files = []
                for file in real_folder.iterdir():
                    try:
                        # I was getting `PermissionError: Operation not permitted: '/proc/1/map_files/400000-423000'`. The file is a symlink, but the
                        # proc directory is special and stat gets confused. Resolving the link first fixes it.
                        files.append( (file.resolve().is_dir(), file.is_symlink(), PurePosixPath(file)) )
                    except:
                        pass # If something goes wrong (file doesn't exist anymore, special files in /proc, etc) just ignore it
                return files
            except: # if folder doesn't exist just return [] for now.
                return [] # TODO should we return None or something instead?

    # The method is used both as a response to a message and in the puzzle code
    def student_cwd(self) -> File:
        """
        Return the student's current working directory. Note that in generation functions, this is different from `File.cwd()`
        File.cwd() returns the current working directory of the generation function, not the student.
        Returns None if shell_pid is not set.
        """
        if self.shell_pid == None:
            return None
        with change_user("root"):
            result = subprocess.check_output(["pwdx", f"{self.shell_pid}"]) # returns "pid: /path/to/folder"
        cwd = result.decode().split(": ", 1)[1][:-1] # Split and remove trailing newline.
        return File(cwd).resolve()

    ### Other methods

    def run(self):
        """
        Sets up a connection between the tutorial inside the docker container and the driving application outside and
        listen for requests from the host.
        """ 

        with Listener(support.conn_addr, authkey = support.conn_key) as listener:
            with listener.accept() as conn:
                # Receive the initial SETUP message.
                message, kwargs = conn.recv()
                if message != Message.SETUP: raise Exception("Expected initial SETUP message.") # TODO custom exception
                conn.send( self.setup(**kwargs) )

                actions = {
                    # Map message type to a function that will be called. The return of the lambda will be sent back to host. 
                    Message.CONNECT_TO_SHELL: self.connect_to_shell,
                    Message.SOLVE: self.solve_puzzle,
                    Message.GET_STUDENT_CWD: lambda: PurePosixPath(self.student_cwd()),
                    Message.GET_FILES: self.get_files,
                }

                while True: # Loop until connection ends.
                    # Messages are send as (MessageEnum, *args) tuples.
                    message, *args = conn.recv()

                    if message == Message.STOP:
                        return
                    else: # call the lambda with *args, send the return value.
                        conn.send(actions[message](*args))