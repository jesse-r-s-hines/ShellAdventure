from __future__ import annotations
from typing import Any, Generator, Iterator, List, Tuple, Dict, ClassVar
from multiprocessing.connection import Client, Connection
import docker, docker.errors, subprocess, os, pickle
from docker.models.images import Image
from docker.models.containers import Container
from pathlib import Path, PurePath, PurePosixPath;
from datetime import datetime, timedelta
from itertools import chain
from textwrap import indent
import yaml, yamale
from yamale.schema import Schema
from . import docker_helper, PKG_PATH
from shell_adventure.shared import messages
from shell_adventure.shared.messages import Message
from shell_adventure.shared.support import PathLike, retry, sentence_list, Tree
from shell_adventure.shared.puzzle_data import PuzzleData
from shell_adventure.shared.tutorial_errors import *

class Tutorial:
    """ Contains the information for a running tutorial. """

    config_file: Path
    """ The path to the config file for this tutorial """

    data_dir: Path
    """ The folder that the config_file is in. Paths in the config_file are relative to here. """

    # Config fields

    image: str
    """ The name or id of the Docker image to run the container in. Defaults to "shell-adventure:latest" """

    container_options: Dict[str, Any]
    """
    Any options you want to pass to the container. These options are passed directly to the docker-py `create()` method.
    See https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.create
    for details on the options you can pass. Most commonly used are `user` and `working_dir`.
    """

    module_paths: List[Path]
    """ List of absolute paths to the puzzle generation modules. """

    name_dictionary: Path
    """ Path to a dictionary containing random names for files. """

    content_sources: List[Path]
    """ A list of files that will be used to generate text content in files. """

    puzzle_templates: List[Tree[str]]
    """ The tree of puzzles templates to use in this tutorial. """

    restart_enabled: bool
    """ Whether restart is enabled or not. """

    show_tree: bool
    """ Whether to show the file tree in the GUI or not. """

    # Other fields
    container: Container
    """ The docker container that the student is in. """

    puzzles: List[Tree[PuzzleData]]
    """ The tree of generated PuzzleData for this tutorial. """
    
    start_time: datetime
    """ Time the tutorial started. """
    end_time: datetime
    """ Time the tutorial ended. """

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
        except (yaml.YAMLError, OSError) as e: # YAML fails to parse, or some filesystem error
            raise ConfigError(str(e))

        def get_path(path: str): return Path(self.data_dir, path).resolve() # Get Path relative to config file

        self.image = config.get("image", "shell-adventure:latest")

        container_options = config.get("container_options", {})
        self.container_options = {str(k): v for k, v in container_options.items()} # Force keys to str

        module_paths: Dict[str, Path] = {}
        for module in config.get("modules"):
            # Files are relative to the config file (if module is absolute, Path will use that, if relative it will join with first)
            module = get_path(module)
            if module.stem in module_paths: # Can't have the same name, even with different paths
                raise ConfigError(f'Multiple puzzle modules with name "{module.stem}" found.') 
            module_paths[module.stem] = module
        self.module_paths = list(module_paths.values())

        self.puzzle_templates = self._parse_puzzles(config.get("puzzles"))

        name_dictionary = config.get("name_dictionary", PKG_PATH / "resources/name_dictionary.txt")
        self.name_dictionary = get_path(name_dictionary)

        self.content_sources = [get_path(f) for f in config.get("content_sources", [])]

        self.restart_enabled = config.get("restart_enabled", True) # PyYAML automatically converts to bool
        self.show_tree = config.get("show_tree", True)

        self.container: Container = None
        self._conn: Connection = None # Connection to send messages to docker container.
        self._logs_stream: Generator[bytes, None, None] = None # The stream that contains the docker side tutorial output.
        self._logs: str = ""
        self._snapshot: Image = None # A docker commit of the image state right after puzzle generation.

        self.puzzles = [] # Populated after _start()

        self.start_time = None
        self.end_time = None

    def _parse_puzzles(self, puzzles) -> List[Tree[str]]:
        """
        Converts YAML output of puzzles into a tree of puzzles.
        ```yaml
        - puzzles.a:
          - puzzles.b:
            - puzzles.c:
              - puzzles.d
              - puzzles.e
              - puzzles.f
        ```
        """
        puzzle_trees: List[Tree[str]] = []
        for puz in puzzles:
            if isinstance(puz, str):
                template, deps = puz, []
            else: # It is a one element dictionary.
                template, deps = list(puz.items())[0]
                if not deps: deps = []
            puzzle_trees.append(Tree(template, children = self._parse_puzzles(deps)))

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
            self._logs += "\n".join((l.decode(errors = "replace") for l in self._logs_stream))
        return self._logs

    def _start_container(self, image: str):
        """ Starts the container and connects to it. """
        try:
            self.container = docker_helper.launch(image, **self.container_options)
        except Exception as e: # If container_options causes an error just raise a ContainerStartupError
           raise ContainerStartupError(f"Tutorial container failed to start:\n{indent(str(e), '  ')}") #https://github.com/docker/docker-py/issues/2860

        try:
            _, self._logs_stream = self.container.exec_run(["python3", "/usr/local/shell_adventure/docker_side/start.py"],
                                                                      user = "root", stream = True)
            # retry the connection a few times since the container may take a bit to get started.
            self._conn = retry(lambda: Client(messages.conn, authkey = messages.conn_key), tries = 20, delay = 0.2)
        except (docker.errors.DockerException, ConnectionError) as e:
            raise ContainerStartupError(
                f"Failed to connect to container:\n{indent(str(e), '  ')}",
                container_logs = self.logs()
            )

    def _stop_container(self):
        """ Stops the container and remove it and the connection to it. """
        if self._conn != None:
            try: self._conn.send( (Message.STOP,) )
            except: pass
            self._conn.close()

        if self.container:
            try: # Force the container to stop (then it will get autoremoved)
                self.container.stop(timeout = 2) # throws NotFound if container already stopped
                # Wait until the container is removed (sometimes it takes a second for the docker api to do so)
                self.container.wait(condition = "removed") # will throw NotFound if already removed
            except docker.errors.NotFound: # Container was already removed
                pass

    def _start(self):
        """
        Starts the tutorial. Launches the container, sets up a connection and generates the puzzles. Used by
        the Tutorial context manager.
        """
        self._start_container(self.image)
        
        try:
            modules = {PurePath(file): file.read_text() for file in self.module_paths}
            name_dictionary = self.name_dictionary.read_text()
            content_sources = [file.read_text() for file in self.content_sources]
        except OSError as e: # some filesystem error
            raise ConfigError(str(e))

        generated_puzzles: List[PuzzleData] = self._send(Message.SETUP, {
            "modules": modules,
            "puzzles": list(chain(*self.puzzle_templates)),
            "name_dictionary": name_dictionary,
            "content_sources": content_sources,
             # If restart is enabled, we need the checkers. Otherwise don't try to dill them and risk pickle errors
            "send_checkers": self.restart_enabled,
        })

        # Convert list of puzzles into tree of same structure as self.puzzle_templates
        def make_puzzles(templates: Tree[str], puzz_iter: Iterator[PuzzleData]) -> Tree[PuzzleData]:
            return Tree(next(puzz_iter), [make_puzzles(child, puzz_iter) for child in templates.children])
        generated_iter = iter(generated_puzzles)
        self.puzzles = [make_puzzles(tree, generated_iter) for tree in self.puzzle_templates]

        if self.restart_enabled:
            self._snapshot = self._commit()

        self.start_time = datetime.now()

    def _stop(self):
        """
        Stop the tutorial, remove the container, and clean up all resources. Used by the Tutorial context manager.
        """
        if not self.end_time: # Check that we haven't already stopped the container
            self.end_time = datetime.now()

            self._stop_container()

            if self._snapshot:
                docker_helper.client.images.remove(image = self._snapshot.id)

    def __enter__(self):
        """
        Launch a tutorial by using it as a context manager, which will launch the tutorial container, generate the puzzles,
        and ensure the container is removed on exit.
        """
        try:
            self._start()
            return self
        except: # If an error occurs in __enter__, __exit__ isn't called.
            self._stop()
            raise # reraise exception

    def __exit__(self, exc_type, exc_value, traceback):
        self._stop()

    def attach_to_shell(self) -> subprocess.Popen:
        """ Attaches to the shell session in the container, making it show in the terminal. Returns the process. """
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

            try:
                modules = {PurePath(file): file.read_text() for file in self.module_paths}
            except OSError as e: # some filesystem error
                raise ConfigError(str(e))
        
            self._send(Message.RESTORE, {
                "modules": modules,
                "puzzles": self.get_all_puzzles(),
            })


    def get_current_puzzles(self) -> List[PuzzleData]:
        """ Returns a list of the currently unlocked puzzles. """
        def get_puzzles(node_list: List[Tree[PuzzleData]]):
            for node in node_list:
                yield node.data
                if node.data.solved:
                    yield from get_puzzles(node.children)

        return list(get_puzzles(self.puzzles))

    def get_all_puzzles(self) -> List[PuzzleData]:
        """ Returns a list of all puzzles (In preorder sequence)."""
        return list(chain(*self.puzzles))

    def solve_puzzle(self, puzzle: PuzzleData, flag: str = None) -> Tuple[bool, str]:
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

