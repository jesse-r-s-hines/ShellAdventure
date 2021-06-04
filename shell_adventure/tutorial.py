from __future__ import annotations, generators
from typing import Generator, List, Tuple, Dict, Any, Callable, ClassVar, Union
import yaml, textwrap
from multiprocessing.connection import Client, Connection
import docker, docker.errors, subprocess
from docker.models.containers import Container
from pathlib import Path, PurePosixPath;
from retry.api import retry_call
from datetime import datetime, timedelta
from . import support
from .support import Puzzle, PathLike, Message, ScriptType, PKG

class PuzzleTree:
    """ A tree node so that puzzles can be unlocked after other puzzles are solved. """
    def __init__(self, generator: str, puzzle: Puzzle = None, dependents: List[PuzzleTree] = None):
        self.generator = generator
        self.puzzle = puzzle
        self.dependents = dependents if dependents else []

    def __iter__(self) -> Generator[PuzzleTree, None, None]:
        """ Iterates over the puzzle tree (preorder) """
        for pt in self.dependents:
            yield pt
            for pt2 in pt:
                yield pt2

class Tutorial:
    """ Contains the information for a running tutorial. """

    config_file: Path
    """ The path to the config file for this tutorial """

    data_dir: Path
    """ This is the path where tutorial files such as puzzles have been placed. """

    # Config fields

    resources: Dict[Path, PurePosixPath]
    """
    Paths to resources that will be put into the container.
    Maps host path to container path. You can copy whole directories.
    However, it will not create parent directories.
    """ 

    setup_scripts: List[Path]
    """
    A list of paths to bash scripts and python scripts that will be run before before puzzle generation.
    The scripts will be run as root.
    """

    module_paths: List[Path]
    """ List of absolute paths to the puzzle generation modules. """

    name_dictionary: Path
    """ Path to a dictionary containing random names for files. """

    content_sources: List[Path]
    """ A list of files that will be used to generate text content in files. """

    puzzles: List[PuzzleTree]
    """ The tree of puzzles in this tutorial. """

    # Other fields
    container: Container
    """ The docker container that the student is in. """
    
    start_time: datetime
    """ Time the tutorial started. """
    end_time: datetime
    """ Time the tutorial ended. """

    def __init__(self, config_file: PathLike):
        """
        Create a tutorial from a config_file.
        Any resources the config file uses should be placed in the same directory as the config file.
        """
        self.config_file = Path(config_file).resolve()
        self.data_dir = self.config_file.parent

        with open(config_file) as temp:
            config = yaml.safe_load(temp)
            # TODO use a custom exception
            if not isinstance(config, dict): raise Exception("Invalid config file.")

        # TODO validation
        self.module_paths = []
        for module in config.get("modules"):
            # Files are relative to the config file (if module is absolute, Path will use that, if relative it will join with first)
            module = Path(self.data_dir, module)
            if not module.exists(): raise FileNotFoundError(f'Module "{module}" not found.')
            if module in self.module_paths: raise Exception(f'Multiple puzzle modules with name "{module.name}" found.')
            self.module_paths.append(module)

        self.puzzles = self._parse_puzzles(config.get("puzzles"))

        self.setup_scripts =  [Path(self.data_dir, f) for f in config.get("setup_scripts", [])] # relative to config file

        resources = config.get("resources", {})
        self.resources = {Path(self.data_dir, src): PurePosixPath("/home/student", dst) for src, dst in resources.items()}

        name_dictionary = config.get("name_dictionary", PKG / "resources/name_dictionary.txt")
        self.name_dictionary = Path(self.data_dir, name_dictionary) # relative to config file

        self.content_sources = [Path(self.data_dir, f) for f in config.get("content_sources", [])] # relative to config file

        self.container = None
        self._conn_to_container: Connection = None # Connection to send messages to docker container.

        self.start_time = None
        self.end_time = None

    def _parse_puzzles(self, puzzles):
        """
        Converts YAML output of puzzles into a PuzzleTree.
        ```yaml
        - puzzles.a:
          - puzzles.b:
            - puzzles.c:
              - puzzles.d
              - puzzles.e
              - puzzles.f
        ```
        """
        puzzle_trees = []
        for puz in puzzles:
            if isinstance(puz, str):
                gen, deps = puz, []
            else: # It is a one element dictionary.
                gen, deps = list(puz.items())[0]
                if not deps: deps = []
            puzzle_trees.append(PuzzleTree(gen, dependents = self._parse_puzzles(deps)))

        return puzzle_trees

    def _launch_container(self, command: Union[List[str], str]) -> Container:
        """ Launches the container with the given command. Returns the container. """
        docker_client = docker.from_env()

        container = docker_client.containers.run('shell-adventure',
            user = "root",
            network_mode = "host",
            command = command,
            cap_add = [
                "CAP_SYS_PTRACE", # Allows us to call `pwdx` to get working directory of student
            ],
            tty = True,
            stdin_open = True,
            # remove = True, # Auto remove makes getting output logs difficult. We'll have to remove the container ourselves.
            detach = True,
        )
        return container
    
    def start(self):
        """
        Starts the tutorial.
        Launches the container, sets up a connection and generates the puzzles.
        In general you should use a tutorial as a context manager instead to start/stop the tutorial, which will
        guarantee that the container gets cleaned up.
        """

        # We can't use "with" since the caller needs to be able to use the tutorial object before it is closed.

        self.container = self._launch_container(["python3", "-m", "shell_adventure_docker.start"])

        try:
            # retry the connection a few times since the container may take a bit to get started.
            self._conn_to_container = retry_call(lambda: Client(support.conn_addr_to_container, authkey = support.conn_key), tries = 20, delay = 0.2)

            # Move resources into container
            for src, dst in self.resources.items():
                subprocess.run(["docker", "cp", src, f"{self.container.id}:{dst}"])
            
            tmp_tree = PuzzleTree("", dependents=self.puzzles) # Put puzzles under a dummy node so we can iterate  it.

            setup_scripts = [] 
            for file in self.setup_scripts:
                if file.suffix == ".py":
                    setup_scripts.append( (ScriptType.PYTHON, file.read_text()) )
                else:
                    setup_scripts.append( (ScriptType.BASH, file.read_text()) )

            self._conn_to_container.send((Message.SETUP, {
                "home": "/home/student",
                "setup_scripts": setup_scripts,
                "modules": {file.stem: file.read_text() for file in self.module_paths},
                "puzzles": [pt.generator for pt in tmp_tree],
                "name_dictionary": self.name_dictionary.read_text(),
                "content_sources": [file.read_text() for file in self.content_sources],
            }))
            generated_puzzles = self._conn_to_container.recv()

            # store the puzzles in the PuzzleTree (unflatten from preorder list)
            for pt, puzzle in zip(tmp_tree, generated_puzzles):
                pt.puzzle = puzzle
        except BaseException as e: # BaseException includes KeyboardInterrupt
            logs = self.stop() # If an error occurs in __enter__, __exit__ isn't called.
            raise TutorialError(f"{type(e).__name__}: {e}", container_logs = logs) from e

        self.start_time = datetime.now()

    def stop(self) -> str:
        """
        Stop the tutorial, clean up all resources. Returns container logs.
        In general you should use a tutorial as a context manager instead to start/stop the tutorial, which will
        guarantee that the container gets cleaned up.
        """
        if not self.end_time: # Check that we haven't already stopped the container
            self.end_time = datetime.now()

            if self._conn_to_container:
                self._conn_to_container.send( (Message.STOP,) )
                self._conn_to_container.close()
            # The container should stop itself, but we'll make sure here as well.
            self.container.stop(timeout = 4)
            logs = self.container.logs()
            self.container.remove()
            
            return logs.decode()
        else:
            return None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logs = self.stop()
        if exc_type and issubclass(exc_type, BaseException):
            raise TutorialError(f"{type(exc_value).__name__}: {exc_value}", container_logs = logs) from exc_value

    def get_current_puzzles(self) -> List[Puzzle]:
        """ Returns a list of the currently unlocked puzzles. """
        def get_puzzles(pt_list: List[PuzzleTree]):
            rtrn = []
            for pt in pt_list:
                rtrn.append(pt.puzzle)
                if pt.puzzle.solved:
                    rtrn.extend(get_puzzles(pt.dependents))
            return rtrn

        return get_puzzles(self.puzzles)

    def get_all_puzzles(self) -> List[Puzzle]:
        """ Returns a list of all puzzles. (In preorder sequence)"""
        tmp_tree = PuzzleTree("", dependents=self.puzzles) # So we can iterate over it.
        return [pt.puzzle for pt in tmp_tree]

    def solve_puzzle(self, puzzle: Puzzle, flag: str = None) -> Tuple[bool, str]:
        """ Tries to solve the puzzle. Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded. """
        self._conn_to_container.send( (Message.SOLVE, puzzle.id, flag) )
        (solved, feedback) = self._conn_to_container.recv()
        puzzle.solved = solved
        return (solved, feedback)

    def connect_to_shell(self, name: str) -> int:
        """
        Connects the tutorial to a running shell session with the given name. The shell session should have a unique name.
        Returns the PID (in docker) of the shell session.
        """
        self._conn_to_container.send( (Message.CONNECT_TO_SHELL, name) )
        return self._conn_to_container.recv() # wait for response

    def get_student_cwd(self) -> PurePosixPath:
        """ Get the path to the students current directory/ """
        self._conn_to_container.send( (Message.GET_STUDENT_CWD,) )
        return self._conn_to_container.recv()

    def get_files(self, folder: PurePosixPath) -> List[Tuple[bool, bool, PurePosixPath]]:
        """
        Returns the children of the given folder in the docker container as a list of (is_dir, is_symlink, path) tuples.
        Folder should be an absolute path.
        """
        assert folder.is_absolute()

        self._conn_to_container.send( (Message.GET_FILES, folder) )
        return self._conn_to_container.recv()

    def time(self) -> timedelta:
        """ Returns the time that the student has spend on the tutorial so far. """
        end_point = self.end_time if self.end_time else datetime.now()
        return (end_point - self.start_time)

    def total_score(self) -> int:
        """ Returns the current score of the student. """
        return sum((puz.score for puz in self.get_all_puzzles()))

    def current_score(self) -> int:
        """ Returns the current score of the student. """
        return sum((puz.score for puz in self.get_all_puzzles() if puz.solved))

    def is_finished(self) -> bool:
        """ Return true if all the puzzles in the tutorial all solved. """
        return all((puz.solved for puz in self.get_all_puzzles()))

class TutorialError(Exception):
    """
    Class for exceptions that occur in the Tutorial.
        container_logs - Output of the container at the time of the exception.
        message - A description of the exception.
    """
    
    def __init__(self, message, container_logs):
        self.container_logs = container_logs
        message = message + "\n\nContainer Logs:\n" + textwrap.indent(self.container_logs, "    ")
        super().__init__(message)