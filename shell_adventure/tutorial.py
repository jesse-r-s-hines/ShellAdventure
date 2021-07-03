from __future__ import annotations
from typing import Any, Generator, List, Tuple, Dict, ClassVar
from multiprocessing.connection import Client, Connection
import docker, docker.errors, subprocess, os, pickle
from docker.models.images import Image
from docker.models.containers import Container
from pathlib import Path, PurePath, PurePosixPath;
from datetime import datetime, timedelta
from . import docker_helper, PKG_PATH
from shell_adventure_shared import support
from shell_adventure_shared.support import PathLike, Message, retry
from shell_adventure_shared.puzzle import Puzzle
from textwrap import indent
import yaml, yamale
from yamale.schema import Schema
from shell_adventure_shared.tutorial_errors import *

class Tutorial:
    """ Contains the information for a running tutorial. """

    config_file: Path
    """ The path to the config file for this tutorial """

    data_dir: Path
    """ This is the path where tutorial files such as puzzles have been placed. """

    image: str
    """ The name or id of the Docker image to run the container in. Defaults to "shell-adventure:latest" """

    # Config fields

    home: PurePosixPath
    """ This is the folder in the container that puzzle generators and checkers will be run in. If None, the WORKDIR of the container will be used. """

    user: str
    """ This is the name of the user that the student is logged in as. If None, the USER of the container will be used. """

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

    restart_enabled: bool
    """ Whether restart is enabled or not. """

    # Static fields
    config_schema: ClassVar[Schema] = yamale.make_schema(PKG_PATH / "config_schema.yaml")

    def __init__(self, config_file: PathLike):
        """ Create a tutorial from a config_file. """
        self.config_file = Path(config_file).resolve()
        self.data_dir = self.config_file.parent

        try:
            data = yamale.make_data(config_file) # Parse the YAML data
            yamale.validate(Tutorial.config_schema, data) # Throws if invalid
            [(config, _)] = data # data is [(data, file_name),...] we should only have one though
        except yamale.YamaleError as e:
            errors = "\n".join(e.results[0].errors)
            raise ConfigError(f'Validation error in "{config_file}":\n{indent(errors, "  ")}')
        except yaml.YAMLError as e:
            raise ConfigError(str(e))

        self.image = config.get("image", "shell-adventure:latest")

        self.home = PurePosixPath(config["home"]) if "home" in config else None # If None, we'll use default home of image
        self.user = config.get("user", None) # If None we'll use default user of image

        module_paths: Dict[str, Path] = {}
        for module in config.get("modules"):
            # Files are relative to the config file (if module is absolute, Path will use that, if relative it will join with first)
            module = Path(self.data_dir, module)
            if not module.exists(): raise FileNotFoundError(f'Module "{module}" not found.') # TODO maybe throw ConfigError instead?
            if module.stem in module_paths: # Can't have the same name, even with different paths
                raise ConfigError(f'Multiple puzzle modules with name "{module.stem}" found.') 
            module_paths[module.stem] = module
        self.module_paths = list(module_paths.values())

        self.puzzles = self._parse_puzzles(config.get("puzzles"))

        name_dictionary = config.get("name_dictionary", PKG_PATH / "resources/name_dictionary.txt")
        self.name_dictionary = Path(self.data_dir, name_dictionary) # relative to config file

        self.content_sources = [Path(self.data_dir, f) for f in config.get("content_sources", [])] # relative to config file

        self.restart_enabled = config.get("restart_enabled", True) # PyYAML automatically converts to bool

        self.container: Container = None
        self._conn: Connection = None # Connection to send messages to docker container.
        self._logs_stream: Generator[bytes, None, None] = None # The stream that contains the docker side tutorial output.
        self._logs: str = ""
        self._snapshot: Image = None # A docker commit of the image state right after puzzle generation.

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


    def _send(self, message: Message, *args) -> Any:
        """ Sends a message to the container, and returns the response. If the container sent an exception, raise it. """
        self._conn.send( (message, *args) )
        try:
            response = self._conn.recv()
        except pickle.PicklingError as e:
            raise e
        except: # The container died without sending any exception info (i.e. Ctrl-D out of bash session)
            raise ContainerStoppedError("Tutorial container stopped unexpectedly.", container_logs = self.logs())
        if isinstance(response, TutorialError):
            raise response # container will send a TutorialError exception if something fails.
        return response


    def logs(self):
        """ Return the container logs so far as a string. """
        if self._logs_stream != None:
            self._logs += "\n".join((l.decode() for l in self._logs_stream))
        return self._logs

    def _start_container(self, image: str):
        """ Starts the container and connects to it. """
        try:
            self.container = docker_helper.launch(image,
                user = self.user,
                working_dir = str(self.home) if self.home else None
            )
            _, self._logs_stream = self.container.exec_run(["python3", "/usr/local/shell_adventure_docker/start.py"],
                                                                      user = "root", stream = True)
            # retry the connection a few times since the container may take a bit to get started.
            self._conn = retry(lambda: Client(support.conn, authkey = support.conn_key), tries = 20, delay = 0.2)
        except (docker.errors.DockerException, ConnectionError) as e:
            raise ContainerStartupError(
                f"Tutorial container failed to start:\n {str(e)}",
                container_logs = self.logs()
            )

    def _stop_container(self):
        """ Stops the container and remove it and the connection to it. """
        if self._conn != None:
            try: self._conn.send( (Message.STOP,) )
            except: pass
            self._conn.close()

        if self.container:
            self.container.stop(timeout = 4) # Force the container to stop
            self.container.remove()

    def start(self):
        """
        Starts the tutorial.
        Launches the container, sets up a connection and generates the puzzles.
        In general you should use a tutorial as a context manager instead to start/stop the tutorial, which will
        guarantee that the container gets cleaned up.
        """
        self._start_container(self.image)
        
        tmp_tree = PuzzleTree("", dependents=self.puzzles) # Put puzzles under a dummy node so we can iterate  it.

        generated_puzzles = self._send(Message.SETUP, {
            "home": self.home,
            "user": self.user,
            "modules": {PurePath(file): file.read_text() for file in self.module_paths},
            "puzzles": [pt.generator for pt in tmp_tree],
            "name_dictionary": self.name_dictionary.read_text(),
            "content_sources": [file.read_text() for file in self.content_sources],
        })

        # store the puzzles in the PuzzleTree (unflatten from preorder list)
        for pt, puzzle in zip(tmp_tree, generated_puzzles):
            pt.puzzle = puzzle

        if any(map(lambda p: p.checker == None, generated_puzzles)): # Check if any puzzle checker failed to pickle
            self.restart_enabled = False # TODO raise warning if restart is disabled because of pickling error

        if self.restart_enabled:
            self._snapshot = self._commit()

        self.start_time = datetime.now()

    def stop(self):
        """
        Stop the tutorial, clean up all resources.
        In general you should use a tutorial as a context manager instead to start/stop the tutorial, which will
        guarantee that the container gets cleaned up.
        """
        if not self.end_time: # Check that we haven't already stopped the container
            self.end_time = datetime.now()

            self._stop_container()

            if self._snapshot:
                docker_helper.client.images.remove(image = self._snapshot.id)

    def __enter__(self):
        try:
            self.start()
            return self
        except: # If an error occurs in __enter__, __exit__ isn't called.
            self.stop()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def attach_to_shell(self) -> subprocess.Popen:
        """ Attaches to the shell session in the container, making it show in the terminal. Returns the process. """
        # docker exec the unix exec bash built-in which lets us change the name of the process
        os.system('cls' if os.name == 'nt' else 'clear') # clear the terminal
        return subprocess.Popen(["docker", "attach", self.container.id])


    def _commit(self):
        """ Return snapshot of the current state of the tutorial """
        return self.container.commit("shell-adventure", f"snapshot-{datetime.now().timestamp()}")

    def restart(self):
        """
        Restart the tutorial and the container to its initial state if possible. Does not regenerate the puzzles,
        so any random values in the puzzles will be the same after the restart.
        """
        if self._snapshot:
            self._stop_container()

            self._start_container(self._snapshot) # Restart the tutorial.

            for puzzle in self.get_all_puzzles(): # Set the puzzle solved state
                puzzle.solved = False

            self._send(Message.RESTORE, {
                "home": self.home,
                "user": self.user,
                "modules": {PurePath(file): file.read_text() for file in self.module_paths},
                "puzzles": [pt.puzzle for pt in PuzzleTree("", dependents = self.puzzles)], # Put puzzles under tree node so we can iterate
            })


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
        (solved, feedback) = self._send(Message.SOLVE, puzzle.id, flag)
        puzzle.solved = solved
        return (solved, feedback)

    def get_student_cwd(self) -> PurePosixPath:
        """ Get the path to the students current directory/ """
        return self._send(Message.GET_STUDENT_CWD)

    def get_files(self, folder: PurePosixPath) -> List[Tuple[bool, bool, PurePosixPath]]:
        """
        Returns the children of the given folder in the docker container as a list of (is_dir, is_symlink, path) tuples.
        Folder should be an absolute path.
        """
        assert folder.is_absolute()
        return self._send(Message.GET_FILES, folder)

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

