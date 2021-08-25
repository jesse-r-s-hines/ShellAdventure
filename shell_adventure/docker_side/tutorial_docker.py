from typing import Callable, List, Tuple, Dict, Any, cast
from types import ModuleType
from pathlib import Path, PurePath, PurePosixPath;
import subprocess, os, pwd, copy
from multiprocessing.connection import Listener
import importlib.util, inspect, traceback
import shell_adventure # For access to globals
from shell_adventure.shared import messages
from shell_adventure.shared.messages import Message
from shell_adventure.shared.support import PathLike, sentence_list, call_with_args, extra_func_params
from shell_adventure.shared.puzzle import Puzzle, PuzzleTemplate
from shell_adventure.shared.puzzle_data import PuzzleData
from shell_adventure.shared.tutorial_errors import *
import shell_adventure.api
from shell_adventure.api.file import File
from shell_adventure.api.permissions import change_user, user_exists
from shell_adventure.api.random_helper import RandomHelper

class TutorialDocker:
    """ Contains the information for a running tutorial docker side. """

    home: Path
    """ This is the folder that puzzle templates and checkers will be run in. Default is the pwd of the bash session. """

    user: str
    """ This is the name of the user that the student is logged in as. Default is the user of the bash session. """

    modules: Dict[str, str]
    """
    Map of the puzzle modules, filename on host mapped to file contents.
    Use str instead of Path since host might be Windows or Linux and WindowsPath != PosixPath
    """

    puzzles: Dict[str, PuzzleData]
    """ Puzzles in this tutorial, mapped to their id. """

    shell_pid: int
    """ The pid of the shell session the tutorial is connected to. """

    rand: RandomHelper
    """ The RandomHelper which will be used when creating random files and folders. """

    def __init__(self):
        """ Create a tutorial. You need to call setup() afterwards to actually set and generate the puzzles etc. """
        # We don't really do anything in here, the tutorial is initialized in the "setup" method when we are actually sent the settings.
        self.home = None
        self.user = None
        self.modules = {} # We keep the modules as strings, so we can reconstruct the traceback if an error is thrown
        self.puzzles = {}
        self.shell_pid: int = 1 # The shell is the main process of the container which is always 1
        self.rand = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager to make sure that the globals set in api are cleared when the tutorial is done.
        This only really matters for tests since normally the container ends if the TutorialDocker does
        """
        shell_adventure.api._home = None
        shell_adventure.api._rand = None

    def _call_user_func(self, func, args = {}) -> Any:
        """ For calling puzzle templates and checkers. Calls func with args, and sets the user and cwd. """
        os.chdir(self.home) # Make sure templates are called with home as the cwd
        with change_user(self.user):
            return call_with_args(func, args)

    def _create_module(self, path: PurePath, code: str) -> ModuleType:
        """ Constructs a module object from a string of python code. Executes the module. """
        spec = importlib.util.spec_from_loader(path.stem, loader = None)
        module = importlib.util.module_from_spec(spec)
        # We don't want the puzzle modules to exist on disk, but exceptions from exec'ed strings don't have as much info
        # If we compile the code with a special "filename", we can inject the file line info into any exceptions that are thrown.
        compiled_code = compile(code, f"<string>:{path}", "exec")

        # execute module in home as user
        self._call_user_func(lambda: exec(compiled_code, module.__dict__))

        return module

    def _get_templates_from_module(self, module: ModuleType) -> Dict[str, PuzzleTemplate]:
        """ Extracts puzzle template functions from a module as a map of {name: func} """
        templates = {}
        for func_name, func in inspect.getmembers(module, inspect.isfunction):
            # Exclude imported functions, lambdas, and private functions
            if func.__module__ == module.__name__ and func.__name__ != "<lambda>" and not func_name.startswith("_"):
                templates[f"{module.__name__}.{func_name}"] = func

        return templates

    def _generate_puzzle(self, template: PuzzleTemplate, template_name: str) -> PuzzleData:
        """ Takes a puzzle template and generates a puzzle from it. """
        args = {
            "home": File(self.home), # can't use home() since the user is actually root.
            "root": File("/"),
        }

        extra_params = extra_func_params(template, list(args.keys()))
        if extra_params:
            raise UserCodeError(
                f'Unrecognized param(s) {sentence_list(extra_params, quote = True)} in puzzle template {template_name}.'
                f' Expected {sentence_list(args.keys(), last_sep = " and/or ", quote = True)}.'
            )
        try:
            puzzle = self._call_user_func(template, args)
        except Exception as e:
            raise UserCodeError(
                f'Puzzle generation failed for template {template_name}:',
                tb_str = self._format_user_exc(e)
            )
        if not isinstance(puzzle, Puzzle):
            raise UserCodeError(f'Puzzle template {template_name} did not return a Puzzle')

        return PuzzleData(template_name, puzzle)

    def _format_user_exc(self, e: Exception) -> str:
        """
        Format an exception in user supplied code. Filters out our code from the traceback so we
        can show only the relevant data to the user, and injects the line data from the original file.
        Since the user code doesn't exist as a file on disk, we need to do some magic on the traceback
        if we want pretty traceback messages.
        """
        # This magically shows line info in tracebacks and errors. I think I got all cases, but its possible that something might break this
        # It would be simpler and more robust to just have puzzles on disk in the container, but that would let the student see them.

        # See https://stackoverflow.com/questions/31949760/how-to-limit-python-traceback-to-specific-files
        frames = []
        for f in traceback.extract_tb(e.__traceback__):
            if f.filename.startswith("<string>:"): # User code, get the line info from the string
                _, path = f.filename.split(":", 1) # "<string>:/path/to/file/on/host/puzzles.py"
                frames.append(traceback.FrameSummary( # See https://docs.python.org/library/traceback.html#framesummary-objects
                    filename = path, lineno = f.lineno, lookup_line = False, locals = None, name = f.name,
                    line = self.modules[path].splitlines()[f.lineno - 1],
                ))
            elif shell_adventure.PKG_PATH not in Path(f.filename).parents: # include library code in the traceback
                frames.append(f)
            # But don't include our code in the traceback, show only the user's code to keep traceback short

        if isinstance(e, SyntaxError) and e.filename.startswith("<string>:"): # Syntax errors need to have the filename fixed as well
            e = copy.copy(e) # shallow copy
            e.filename = e.filename.split(":", 2)[1]

        lines = traceback.format_list(frames) + traceback.format_exception_only(type(e), e)
        return "Traceback (most recent call last):\n" + "".join(lines)

    def _dill_checker(self, puzzle: PuzzleData) -> PuzzleData:
        """ Returns a packed version of the puzzle. Throws detailed error if pickling fails. """
        try:
            return puzzle.checker_dilled()
        except Exception as e: # Quite a few things can go wrong, RecursionError, PickleError, TypeError...
            raise UserCodeError(
                f"Unpickleable autograder function in '{puzzle.template}'. In order to use restart functionality, your "
                 "autograder functions must be serializable using the dill module. Either set restart_enabled to False "
                 "or remove the unpickleable object. See https://dill.readthedocs.io/en/latest/index.html#major-features "
                 "for what objects dill can serialize. The error dill threw was:\n\n" + format_exc_only(e)
            )

    def _common_setup(self, home: PathLike = None, user: str = None, rand: RandomHelper = None):
        """
        Does some shared setup between setup and restore methods.
        Sets home, user, and rand. If home and user are None they default to home and user of the
        shell session. Checks if home and user are valid. And initializes the global variables needed
        for the api to work.
        """
        self.home = Path(home if home else self.student_cwd()).resolve()
        # see https://stackoverflow.com/questions/5327707/how-could-i-get-the-user-name-from-a-process-id-in-python-on-linux
        self.user = user if user else pwd.getpwuid(Path(f"/proc/{self.shell_pid}").stat().st_uid).pw_name

        if not self.home.exists() or not self.home.is_dir():
            raise ConfigError(f'"{self.home}" doesn\'t exist or isn\'t a directory')
        if not user_exists(self.user): raise ConfigError(f'"{self.user}" doesn\'t exist')

        self.rand = rand

        # Unfortunately we have to have some package level variables to allow File methods to access
        # the RandomHelper and student home
        shell_adventure.api._home = File(self.home)
        shell_adventure.api._rand = self.rand


    ### Message actions, these functions can be called by sending a message over the connection

    def setup(self, *, home: PathLike = None, user: str = None, modules: Dict[PurePath, str], puzzles: List[str],
              name_dictionary: str, content_sources: List[str], send_checkers: bool) -> List[PuzzleData]:
        """
        Initializes the tutorial with the given settings. Generates the puzzles in the modules. The
        initialization is done separate from the constructor so that it can be done after the connection
        with the host is setup. Returns the generated puzzles as a list.
        """
        # Unfortunately we have to have some package level variables allow File methods to access the RandomHelper and TutorialDocker
        rand = RandomHelper(name_dictionary, content_sources)
        self._common_setup(home, user, rand)
        self.modules = {str(path): content for path, content in modules.items()}

        try: # Load modules
            modules_list = [self._create_module(path, code) for path, code in modules.items()]
        except Exception as e:
            raise UserCodeError(f'Puzzle generation failed:', tb_str = self._format_user_exc(e))

        # Get puzzle templates from the modules
        templates: Dict[str, PuzzleTemplate] = {}
        for module in modules_list:
            templates.update( self._get_templates_from_module(module) )

        unknown_puzzles = [p for p in puzzles if p not in templates]
        if unknown_puzzles: raise ConfigError(f"Unknown puzzle template(s) {sentence_list(unknown_puzzles, quote = True)}")

        # Generate the puzzles
        puzzle_list: List[PuzzleData] = [self._generate_puzzle(templates[template], template) for template in puzzles]
        self.puzzles = {p.id: p for p in puzzle_list}

        # Reset rand after generation is complete. You can't use it during the tutorial since we don't restore it on restart
        shell_adventure.api._rand = None

        if send_checkers:
            # Pickle the checkers before sending. Throw detailed error if dill fails
            puzzle_list = [self._dill_checker(puzz) for puzz in puzzle_list]
        else: # Just strip out the checkers if we don't need to send them. We only need to send the checker if restart is enabled.
            puzzle_list = [p.checker_stripped() for p in puzzle_list]

        return puzzle_list

    def restore(self, *, home: PathLike = None, user: str = None, modules: Dict[PurePath, str], puzzles: List[PuzzleData]):
        """
        Restore the tutorial after we've loading a snapshot. This is for usage after a restart. Docker commit keeps all filesystem state, but
        we have to restart the container and processes. We don't need to regenerate the puzzles, but we do need to resend the puzzle objects
        so we can use the checkers.
        """
        self._common_setup(home, user)
        self.modules = {str(path): content for path, content in modules.items()}

        # Convert the pickled checker back into a function
        self.puzzles = {p.id: p.checker_undilled() for p in puzzles}

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
        try:
            checker_result = self._call_user_func(cast(Callable, puzzle.checker), args)
        except Exception as e:
            raise UserCodeError(
                f'Puzzle autograder for template {puzzle.template} failed:',
                tb_str = self._format_user_exc(e)
            )

        solved = False
        if checker_result == True:
            solved = True
            feedback = "Correct!"
        elif checker_result == False:
            feedback = "Incorrect!"
        elif isinstance(checker_result, str):
            feedback = checker_result
        else:
            type_name = type(checker_result).__name__
            raise UserCodeError(
                f'Autograder for puzzle template {puzzle.template} returned {type_name}, expected bool or str.'
            )

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
        # Host a port "publicly". We'll map it to localhost via Docker.
        with Listener(('0.0.0.0', messages.port), authkey = messages.conn_key) as listener:
            with listener.accept() as conn:
                try:
                    # Receive the initial setup message.
                    actions = { # Map message type to a function that will be called. The return of the lambda will be sent back to host.
                        Message.SETUP: self.setup,
                        Message.RESTORE: self.restore,
                    }
                    message, *args = conn.recv()
                    if message not in actions: raise ValueError(f"Expected initial SETUP or RESTORE message, got {message}.")
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
                            if message not in actions: raise ValueError(f"Unrecognized message {message}.")
                            conn.send(actions[message](*args))
                except TutorialError as e:
                    conn.send(e)
                except BaseException as e: # Any other exception will get wrapped
                    conn.send(UnhandledError("An error occurred in the container:", tb_str = format_exc(e)))