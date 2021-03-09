from typing import List, Tuple, Dict, Any, Callable, ClassVar, Union
import yaml, shutil
from multiprocessing.connection import Client, Connection
import docker, docker.errors
from docker.models.containers import Container
from pathlib import Path;
from . import support
from .support import Puzzle, PuzzleTree, PathLike, Message
import tempfile
import textwrap
from retry.api import retry_call

class Tutorial:
    """ Contains the information for a running tutorial. """

    config_file: Path
    """ The path to the config file for this tutorial """

    data_dir: Path
    """ This is the path where tutorial files such as puzzles have been placed. """

    container: Container
    """ The docker container that the student is in. """
    
    puzzles: List[PuzzleTree]
    """ The tree of puzzles in this tutorial. """

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

        self.module_paths: List[Path] = []
        for module in config.get("modules"):
            # Files are relative to the config file (if module is absolute, Path will use that, if relative it will join with first)
            module = Path(self.data_dir, module)
            if not module.exists(): raise FileNotFoundError(f'Module "{module}" not found.')
            if module in self.module_paths: raise Exception(f'Multiple puzzle modules with name "{module.name}" found.')
            self.module_paths.append(module)

        self.puzzles = [PuzzleTree(gen) for gen in config.get("puzzles")]

        self._volume: tempfile.TemporaryDirectory = None # The volume that the container is using.
        self.container = None
        self._conn: Connection = None # Connection to the docker container.

    def _gather_files(self, volume: Path):
        """ Moves the files for the tutorial into self.volume. """
        # if not resources: resources = []

        # Gather puzzle modules and put them in container volume
        (volume / "modules").mkdir()
        for module in self.module_paths:
            dest = volume / "modules" / module.name
            shutil.copyfile(module, dest) # Copy to volume

        # TODO add this to config file
        # (volume / "resources").mkdir()
        # for resource in resources:
        #     dest = volume / "resources" / resource.name
        #     shutil.copyfile(resource, dest) # Copy to volume

    def _launch_container(self, volume: str, command: Union[List[str], str]):
        """
        Launches the container with the given command. Returns the container.
        The volume will be mapped to /tmp/shell-adventure/ in the container.
        """
        docker_client = docker.from_env()

        container = docker_client.containers.run('shell-adventure',
            user = "root",
            # Make a volume to share our puzzle files with the container.
            volumes = {volume: {'bind': '/tmp/shell-adventure', 'mode': 'rw'}},
            network_mode = "host",
            command = command,

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

        # We can't use "with" since we the caller to be able to use the tutorial object before it is closed.
        
        self._volume = tempfile.TemporaryDirectory(prefix="shell-adventure-")
        self._gather_files(Path(self._volume.name)) # Gather modules and resources into the volume.
        self.container = self._launch_container(self._volume.name,
            ["python3", "-m", "shell_adventure_docker.start", "/tmp/shell-adventure"]
        )

        try:
            # retry the connection a few times since the container may take a bit to get started.
            self._conn = retry_call(lambda: Client(support.conn_addr, authkey = support.conn_key), tries = 20, delay = 0.2)
            self._conn.send( (Message.GENERATE, [pt.generator for pt in self.puzzles]) )
            generated_puzzles = self._conn.recv()

            # store the puzzles in the PuzzleTree
            for pt, puzzle in zip(self.puzzles, generated_puzzles):
                pt.puzzle = puzzle
        except BaseException as e: # BaseException includes KeyboardInterrupt
            logs = self.stop() # If an error occurs in __enter__, __exit__ isn't called.
            raise TutorialError("An error occurred while generating puzzles.", container_logs = logs) from e

    def stop(self):
        """
        Stop the tutorial, clean up all resources. Returns container logs.
        In general you should use a tutorial as a context manager instead to start/stop the tutorial, which will
        guarantee that the container gets cleaned up.
        """
        if self._conn:
            self._conn.send("END")
            self._conn.close()
        # The container should stop itself, but we'll make sure here as well.
        self.container.stop(timeout = 4)
        logs = self.container.logs()
        self.container.remove()
        self._volume.cleanup()
        
        return logs.decode()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def solve_puzzle(self, puzzle: Puzzle, flag: str = None) -> Tuple[bool, str]:
        """ Tries to solve the puzzle. Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded. """
        try:
            self._conn.send( (Message.SOLVE, puzzle.id) )
            (solved, feedback) = self._conn.recv()
            puzzle.solved = solved
            return (solved, feedback)
        except BaseException as e:
            logs = self.stop()
            raise TutorialError(f'An error occurred while solving puzzle {puzzle.id}: "{puzzle.question}"', container_logs = logs) from e

    def connect_to_bash(self):
        """ Connects the tutorial to a running bash session. Returns the PID (in docker) of the bash session. """
        try:
            self._conn.send( (Message.CONNECT_TO_BASH,) )
            return self._conn.recv() # wait for response
        except BaseException as e:
            logs = self.stop()
            raise TutorialError(f'An error occurred while connecting to bash.', container_logs = logs) from e

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