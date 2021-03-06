from __future__ import annotations # Don't evaluate annotations until after the module is run.
from typing import List, Tuple, Dict, Any, Callable, ClassVar, Union
from types import ModuleType
import os, yaml, subprocess, shutil
from multiprocessing.connection import Listener, Connection
import importlib.util, inspect
import docker, docker.errors
from pathlib import Path;
from threading import Thread
from .support import Puzzle, PathLike
import tempfile
from . import gui

class Tutorial:
    """ Contains the information for a running tutorial. """

    config_file: Path
    """ The path to the config file for this tutorial """

    data_dir: Path
    """ This is the path where tutorial files such as puzzles have been placed. """

    container: docker.Container
    """ The docker container that the student is in. """
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
        self.puzzle_names: List[str] = config.get("puzzles", [])
        self.puzzles = []

        self._volume: tempfile.TemporaryDirectory = None # The volume that the container is using.
        self.container = None
        self._logs = None
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
        # Start the container
        docker_client = docker.from_env()

        container = docker_client.containers.run('shell-adventure',
            user = "root",
            # Make a volume to share our puzzle files with the container.
            volumes = {volume: {'bind': '/tmp/shell-adventure', 'mode': 'rw'}},
            network_mode = "host",
            command = command,

            tty = True,
            stdin_open = True,
            remove = True,
            detach = True,
        )
        return container

        # TODO handle container errors
        # logs = container.attach(stdout=True, stderr=True, stream = True, logs = True)
        # try:
        #     dockerpty.exec_command(docker_client.api, container.id, "sudo -i -u student bash")
        # except:
        #     pass
        # return "\n".join([l.decode() for l in logs])

        # try:
        #   # Make container. I can use this code once If got a terminal running inside docker, and don't have to detach
        # except docker.errors.ContainerError as e:
        #     print(f"Docker container failed with exit code {e.exit_status}. Output was:\n")
        #     print(e.stderr.decode().strip())
    
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
        self._logs = self.container.attach(stdout=True, stderr=True, stream = True, logs = True)

        # TODO add checks for if error occurs in container
        address = ('localhost', 6000) # TODO move address into support
        self._listener = Listener(address, authkey = b'shell_adventure')
        self._conn = self._listener.accept()

        self._conn.send(self.puzzle_names)
        puzzles = self._conn.recv()
        for gen, puz in zip(self.puzzle_names, puzzles):
            # TODO Maybe send puzzles directly.
            puz = Puzzle(question = puz["question"], score = puz["score"], checker = None)
            self.puzzles.append(Tutorial.PuzzleTree(gen, puz))

    def stop(self):
        """ Stop the tutorial, clean up all resources. """
        self._conn.send("END")
        # The container should stop and remove itself now.
        self._conn.close()
        self._listener.close()

        print("Container output:") # TODO clean this up
        print("    \n".join([l.decode() for l in self._logs]))
        print("End container output")
        self._volume.cleanup()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def solve_puzzle(self, puzzle: int, flag: str = None) -> Tuple[bool, str]:
        """ Tries to solve the puzzle by its index. Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded. """
        self._conn.send(puzzle)
        return self._conn.recv()