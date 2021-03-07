from __future__ import annotations # Don't evaluate annotations until after the module is run.
from typing import List, Tuple, Dict, Any, Callable, ClassVar, Union
from types import ModuleType
import os, yaml, subprocess, shutil
from multiprocessing.connection import Listener, Connection
import importlib.util, inspect
import docker, docker.errors
from pathlib import Path;
from threading import Thread
from .support import Puzzle, PathLike, conn_addr, conn_key
import tempfile
from . import gui
import textwrap

class Tutorial:
    """ Contains the information for a running tutorial. """

    config_file: Path
    """ The path to the config file for this tutorial """

    data_dir: Path
    """ This is the path where tutorial files such as puzzles have been placed. """

    container: docker.Container
    """ The docker container that the student is in. """
    
    #TODO move into support?
    class PuzzleTree:
        """ A tree node so that puzzles can be unlocked after other puzzles are solved. """
        def __init__(self, generator: str, puzzle: Puzzle = None, dependents: List[Puzzle] = None):
            self.generator = generator
            self.puzzle = puzzle
            self.dependents = dependents if dependents else []

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
            # TODO validate config.

        self.module_names: List[str] = config.get("modules", [])
        self.puzzles = [Tutorial.PuzzleTree(gen) for gen in config.get("puzzles", [])]

        self._volume: tempfile.TemporaryDirectory = None # The volume that the container is using.
        self.container = None
        self._listener: Listener = None # Listener to the docker container
        self._conn: Connection = None # Connection to the docker container.

    def _gather_files(self, volume: Path):
        """ Moves the files for the tutorial into self.volume. """
        # if not resources: resources = []

        # Gather puzzle modules and put them in container volume
        (volume / "modules").mkdir()
        for module in self.module_names:
            # Files are relative to the config file (if module is absolute, Path will use that, if relative it will join with first)
            module = Path(self.data_dir, module)
            dest = volume / "modules" / module.name
            if dest.exists():
                raise Exception(f"Two puzzle modules with name {module.name} found.")
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
        """

        # We can't use "with" since we the caller to be able to use the tutorial object before it is closed.
        
        self._volume = tempfile.TemporaryDirectory(prefix="shell-adventure-")
        self._gather_files(Path(self._volume.name)) # Gather modules and resources into the volume.
        self.container = self._launch_container(self._volume.name,
            ["python3", "-m", "shell_adventure_docker.start", "/tmp/shell-adventure"]
        )

        try:
            self._listener = Listener(conn_addr, authkey = conn_key)
            self._conn = self._listener.accept()

            self._conn.send([pt.generator for pt in self.puzzles])
            generated_puzzles = self._conn.recv()

            # store the puzzles in the PuzzleTree
            for pt, response in zip(self.puzzles, generated_puzzles):
                # TODO Maybe send puzzles directly.
                puz = Puzzle(question = response["question"], score = response["score"], checker = None)
                puz.id = response["id"]
                pt.puzzle = puz
        except BaseException as e: # BaseException includes KeyboardInterrupt
            logs = self.container.attach(stdout = True, stderr = True, logs = True)
            self.stop() # If an error occurs in __enter__, __exit__ isn't called.
            raise TutorialError("An error occurred while generating puzzles.", container_logs = logs) from e

    def stop(self):
        """ Stop the tutorial, clean up all resources. """
        if self._conn:
            self._conn.send("END")
            self._conn.close()
        self._listener.close()
        # The container should stop itself, but we'll make sure here as well.
        self.container.stop(timeout = 4)
        self.container.remove()
        self._volume.cleanup()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def solve_puzzle(self, puzzle: Puzzle, flag: str = None) -> Tuple[bool, str]:
        """ Tries to solve the puzzle. Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded. """

        try:
            self._conn.send(puzzle.id)
            (solved, feedback) = self._conn.recv()
            puzzle.solved = solved
            return (solved, feedback)
        except BaseException as e:
            logs = self.container.attach(stdout = True, stderr = True, logs = True)
            raise TutorialError(f'An error occurred while solving puzzle {puzzle.id}: "{puzzle.question}"', container_logs = logs) from e


class TutorialError(Exception):
    """
    Class for exceptions that occur in the Tutorial.
        container_logs - Output of the container at the time of the exception.
        message - A description of the exception.
    """
    
    def __init__(self, message, container_logs):
        self.container_logs = container_logs.decode()
        message = message + "\n\nContainer Logs:\n" + textwrap.indent(self.container_logs, "    ")
        super().__init__(message)