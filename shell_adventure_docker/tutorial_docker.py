from tempfile import TemporaryDirectory
from typing import Callable, List, Tuple, Dict, Any, cast
from types import ModuleType
from pathlib import Path, PurePosixPath;
import subprocess, os
from multiprocessing.connection import Listener
import inspect
from . import support
from .support import Puzzle, PathLike, Message, PuzzleGenerator, retry
from .file import File
from .permissions import change_user, user_exists
from .random_helper import RandomHelper
import shell_adventure_docker # For access to globals
from .exceptions import * # Order matters here, we need to register exceptions as picklable after they are defined.

class TutorialDocker:
    """ Contains the information for a running tutorial docker side. """

    home: Path
    """ This is the folder that puzzle generators and checkers will be run in. """

    user: str
    """ This is the name of the user that the student is logged in as. """

    puzzles: Dict[str, Puzzle]
    """ Puzzles in this tutorial, mapped to their id. """

    shell_pid: int
    """ The pid of the shell session the tutorial is connected to. """

    def __init__(self):
        """ Create a tutorial. You need to call setup() afterwards to actually set and generate the puzzles etc. """
        # We don't really do anything in here, the tutorial is initialized in the "setup" method when we are actually sent the settings.
        self.home = None
        self.user = None
        self.puzzles = {}
        self.shell_pid: int = 1 # The shell is the main process of the container which is always 1

    @staticmethod
    def _create_module(name: str, code: str) -> ModuleType:
        """ Constructs a module object from a string of python code. Executes the module. """
        module = ModuleType(name)
        exec(code, module.__dict__) # Uses funcs as globals.
        return module

    @staticmethod
    def _get_generators_from_module(module: ModuleType) -> Dict[str, PuzzleGenerator]:
        """ Extracts puzzle generator functions from a module as a map of {name: func} """
        generators = {}
        for func_name, func in inspect.getmembers(module, inspect.isfunction):
            # Exclude imported functions, lambdas, and private functions
            if func.__module__ == module.__name__ and func.__name__ != "<lambda>" and not func_name.startswith("_"):
                generators[f"{module.__name__}.{func_name}"] = func

        return generators

    def _call_user_func(self, func, args) -> Any:
        """ For calling puzzle generators and checkers. Calls func with args, and sets the user, cwd, and umask. """
        os.chdir(self.home) # Make sure generators are called with home as the cwd
        os.umask(0o000) # By default, python won't make any files writable by "other". This turns that off.
        with change_user(self.user):
            return support.call_with_args(func, args)
            # TODO error checking

    def _generate_puzzle(self, generator: PuzzleGenerator) -> Puzzle:
        """ Takes a puzzle generator and generates a puzzle from it. """
        return self._call_user_func(generator, { # TODO add documentation for args you can take in generator function
            "home": File(self.home), # can't use home() since the user is actually root. #TODO add docs that File.home() doesn't work as expected. 
            "root": File("/"),
        })


    ### Message actions, these functions can be called by sending a message over the connection
    
    def setup(self, home: PathLike, user: str, resources: Dict[PurePosixPath, bytes], setup_scripts: List[Tuple[str, str]], modules: Dict[str, str], puzzles: List[str],
              name_dictionary: str, content_sources: List[str]) -> List[Puzzle]:
        """
        Initializes the tutorial with the given settings. Generates the puzzles in the modules.
        The initialization is done separate from the constructor so that it can be done after the connection with the host is setup.
        Returns the generated puzzles as a list.
        """
        # Unfortunately we have to have some package level variables allow File methods to access the RandomHelper and TutorialDocker
        shell_adventure_docker._tutorial = self
        shell_adventure_docker.rand = RandomHelper(name_dictionary, content_sources)

        self.home = Path(home).resolve()
        self.user = user
        if not self.home.exists() or not self.home.is_dir():
            raise TutorialConfigException(f'"{self.home}" doesn\'t exist or isn\'t a directory')
        if not user_exists(self.user): raise TutorialConfigException(f'"{self.user}" doesn\'t exist')

        # Copy resources
        for dest, content in resources.items():
            destPath = File(self.home, dest) # resource paths are relative to home.
            destPath.parent.mkdir(parents = True, exist_ok = True)
            destPath.write_bytes(content)
            destPath.chown(self.user, self.user)

        # Run setup scripts
        with TemporaryDirectory("-shell-adventure-scripts") as dir:
            for name, script in setup_scripts:
                os.chdir(self.home) # Run scripts from home
                if name.endswith(".py"): # This will execute the module. We don't need to keep it since we aren't going to use its functions
                    with change_user(self.user):
                        TutorialDocker._create_module("<string>", script) 
                else:
                    file = File(dir, name)
                    file.create(mode = 0o700, content = script) # Make script executable
                    subprocess.run([file], shell = True, check = True) # throw error if fail # Run bash scripts as root.

        # Load modules
        modules_list = [TutorialDocker._create_module(name, code) for name, code in modules.items()]

        # Get puzzle generators from the modules
        generators: Dict[str, PuzzleGenerator] = {}
        for module in modules_list: 
            generators.update( TutorialDocker._get_generators_from_module(module) )

        unknown_puzzles = set(puzzles) - set(generators.keys())
        if unknown_puzzles: raise Exception(f"Unknown puzzle generators: {', '.join(unknown_puzzles)}") # TODO custom exception
        puzzle_list: List[Puzzle] = [self._generate_puzzle(generators[gen]) for gen in puzzles]

        self.puzzles = {p.id: p for p in puzzle_list}

        # Reset rand after generation is complete. You can't use it during the tutorial since we don't restore it on undo
        shell_adventure_docker.rand = None

        return puzzle_list

    def restore(self, home: PathLike, user: str, puzzles: List[Puzzle]):
        """
        Restore the tutorial after we've loading a snapshot. This is for usage after an undo. Docker commit keeps all filesystem state, but
        we have to restart the container and processes. We don't need to regenerate the puzzles, but we do need to resend the puzzle objects so
        we can use the checkers.
        """
        # TODO Refactor this to not be so duplicated
        self.home = Path(home).resolve()
        self.user = user

        shell_adventure_docker._tutorial = self
        self.puzzles = {p.id: p for p in puzzles}
        for puz in self.puzzles.values(): puz.extract() # Convert the pickled checker back into a function


    def solve_puzzle(self, puzzle_id: str, flag: str = None) -> Tuple[bool, str]:
        """
        Tries to solve the puzzle with the given id.
        Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded.
        """
        puzzle = self.puzzles[puzzle_id]

        args: Dict[str, Any] = {
            # "output": output,
            "flag": flag,
            "cwd": self.student_cwd(),
        }
        checker_result = self._call_user_func(cast(Callable, puzzle.checker), args)

        solved = False
        if checker_result == True:
            solved = True
            feedback = "Correct!"
        elif checker_result == False:
            feedback = "Incorrect!"
        elif isinstance(checker_result, str):
            feedback = checker_result
        else:
            raise Exception(f'Checker function for puzzle "{puzzle.question}" returned {type(checker_result).__name__}, bool or str expected.')

        puzzle.solved = solved
        return (solved, feedback)

    def get_files(self, folder: PathLike) -> List[Tuple[bool, bool, PurePosixPath]]:
        """
        Returns a list of files under the given folder as a list of (is_dir, is_symlink, path) tuples.
        folder should be an absolute path.
        """
        real_folder = Path(folder) # convert to real PosixPath
        assert real_folder.is_absolute()
        # Convert to PurePosixPath since we are going to send it over to a system that may be Windows. And the file doesn't exist on host.
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
        """
        result = subprocess.check_output(["pwdx", f"{self.shell_pid}"]) # returns "pid: /path/to/folder"
        cwd = result.decode().split(": ", 1)[1][:-1] # Split and remove trailing newline.
        return File(cwd).resolve()

    ### Other methods

    def run(self):
        """
        Sets up a connection between the tutorial inside the docker container and the driving application outside and
        listen for requests from the host.
        """ 
        with Listener(support.conn_addr_to_container, authkey = support.conn_key) as listener:
            with listener.accept() as conn:
                try:
                    # Receive the initial setup message.
                    actions = { # Map message type to a function that will be called. The return of the lambda will be sent back to host.
                        Message.SETUP: self.setup,
                        Message.RESTORE: self.restore,
                    }
                    message, *args = conn.recv()
                    if message not in actions: raise Exception(f"Expected initial SETUP or RESTORE message, got {message}.")
                    conn.send(actions[message](**args[0]))

                    actions = {
                        # Map message type to a function that will be called. The return of the lambda will be sent back to host.
                        Message.SOLVE: self.solve_puzzle,
                        Message.GET_STUDENT_CWD: lambda: PurePosixPath(self.student_cwd()),
                        Message.GET_FILES: self.get_files,
                    }

                    while True: # Loop until connection ends.
                        message, *args = conn.recv() # Messages are sent as (MessageEnum, *args) tuples.

                        if message == Message.STOP:
                            return
                        else: # call the lambda with *args, send the return value.
                            if message not in actions: raise Exception(f"Unrecognized message {message}.")
                            conn.send(actions[message](*args)) 
                except BaseException as e: # BaseException includes KeyboardInterrupt
                    conn.send(e)