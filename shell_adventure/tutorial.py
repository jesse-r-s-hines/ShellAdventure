from __future__ import annotations
from typing import Any, Generator, List, Tuple, Dict, ClassVar
from multiprocessing.connection import Listener, Client, Connection
import docker, docker.errors, subprocess, os
from threading import Thread
from docker.models.images import Image
from docker.models.containers import Container
from pathlib import Path, PurePosixPath;
from datetime import datetime, timedelta
from . import docker_helper, PKG_PATH
from shell_adventure_docker import support
from shell_adventure_docker.support import PathLike, Message, retry
from shell_adventure_docker.puzzle import Puzzle
from textwrap import indent
import yaml, yamale
from yamale.schema import Schema
from shell_adventure_docker.tutorial_errors import * # Order matters here, we need to register exceptions as picklable after they are defined.

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
    """ This is the folder in the container that puzzle generators and checkers will be run in. Defaults to the WORKDIR of the container. """

    user: str
    """ This is the name of the user that the student is logged in as. Defaults to the USER of the container. """

    resources: Dict[Path, PurePosixPath]
    """
    Paths to resources that will be put into the container.
    Maps host path to container path. Container path is relative to home.
    You can copy whole directories and it will create parent directories.
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

    undo_enabled: bool
    """ Whether undo is enabled or not. """

    undo_list: List[Snapshot]
    """ A list of Snapshots that store the state after each command the student enters. """

    # Static fields
    config_schema: ClassVar[Schema] = yamale.make_schema(PKG_PATH / "config_schema.yaml")

    def __init__(self, config_file: PathLike):
        """
        Create a tutorial from a config_file.
        Any resources the config file uses should be placed in the same directory as the config file.
        """
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

        home = (config.get("home") or # Use config home if it exists else image WorkingDir if it exists else "/"
                docker_helper.client.api.inspect_image(self.image)["Config"]["WorkingDir"] or
                "/")
        self.home = PurePosixPath(home)

        self.user = (config.get("user") or # use config user if it exists else image User if it exists else root
                     docker_helper.client.api.inspect_image(self.image)["Config"]["User"] or
                     "root")

        self.module_paths = []
        for module in config.get("modules"):
            # Files are relative to the config file (if module is absolute, Path will use that, if relative it will join with first)
            module = Path(self.data_dir, module)
            if not module.exists(): raise FileNotFoundError(f'Module "{module}" not found.') # TODO maybe throw ConfigError instead?
            if module in self.module_paths: raise ConfigError(f'Multiple puzzle modules with name "{module.name}" found.')
            self.module_paths.append(module)

        self.puzzles = self._parse_puzzles(config.get("puzzles"))

        self.setup_scripts =  [Path(self.data_dir, f) for f in config.get("setup_scripts", [])] # relative to config file

        resources = config.get("resources", {})
        self.resources = {Path(self.data_dir, src): PurePosixPath(dst) for src, dst in resources.items()} # dst will be interpreted as relative to home in the container.

        name_dictionary = config.get("name_dictionary", PKG_PATH / "resources/name_dictionary.txt")
        self.name_dictionary = Path(self.data_dir, name_dictionary) # relative to config file

        self.content_sources = [Path(self.data_dir, f) for f in config.get("content_sources", [])] # relative to config file

        self.undo_enabled = config.get("undo", True) # PyYAML automatically converts to bool


        self.container: Container = None
        self._conn_to_container: Connection = None # Connection to send messages to docker container.
        self._listener_thread: Thread = None # Thread running a Listener that will trigger the docker commits.
                                             # The Docker container should send a signal after every bash command the student enters.
        self._container_logs: Generator[bytes, None, None] = None # The stream that contains the docker side tutorial output.

        self.undo_list = []

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

    def _listen(self):
        """
        Listen for the docker container to tell us when a command has been entered.
        Launch in a separate thread.
        """
        with Listener(support.conn_addr_from_container, authkey = support.conn_key) as listener:
            while True:
                with listener.accept() as conn:
                    data = conn.recv()
                    if data == Message.STOP:
                        return
                    elif data == Message.MAKE_COMMIT:
                        self.commit()

    def _recv(self) -> Any:
        """ Receives a value from the connection to the container. If the container sent an exception, raise it. """
        data = self._conn_to_container.recv()
        if isinstance(data, BaseException): raise data
        return data

    def _start_container(self, image: str):
        """ Starts the container and connects to it. """
        try:
            self.container = docker_helper.launch(image,
                user = self.user,
                working_dir = str(self.home)
            )
            _, self._container_logs = self.container.exec_run(["python3", "/usr/local/shell_adventure_docker/start.py"],
                                                                user = "root", stream = True)
            # retry the connection a few times since the container may take a bit to get started.
            self._conn_to_container = retry(lambda: Client(support.conn_addr_to_container, authkey = support.conn_key), tries = 20, delay = 0.2)
        except Exception as e:
            logs = "\n".join((l.decode() for l in self._container_logs))
            raise ContainerError("Tutorial container failed to start.", container_logs = logs) from e

    def _stop_container(self):
        """ Stops the container and remove it and the connection to it. """
        if self._conn_to_container != None:
            self._conn_to_container.send( (Message.STOP,) )
            self._conn_to_container.close()

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

        self._conn_to_container.send((Message.SETUP, {
            "home": self.home,
            "user": self.user,
            "resources": {dst: src.read_bytes() for src, dst in self.resources.items()},
            "setup_scripts": [(str(file), file.read_text()) for file in self.setup_scripts],
            "modules": {file.stem: file.read_text() for file in self.module_paths},
            "puzzles": [pt.generator for pt in tmp_tree],
            "name_dictionary": self.name_dictionary.read_text(),
            "content_sources": [file.read_text() for file in self.content_sources],
        }))
        generated_puzzles = self._recv()

        # store the puzzles in the PuzzleTree (unflatten from preorder list)
        for pt, puzzle in zip(tmp_tree, generated_puzzles):
            pt.puzzle = puzzle

        if any(map(lambda p: p.checker == None, generated_puzzles)): # Check if any puzzle checker failed to pickle
            self.undo_enabled = False # TODO raise warning if undo is disabled because of pickling error

        # self._listener_thread = Thread(target=self._listen)
        # self._listener_thread.start()

        self.start_time = datetime.now()

    def stop(self):
        """
        Stop the tutorial, clean up all resources
        In general you should use a tutorial as a context manager instead to start/stop the tutorial, which will
        guarantee that the container gets cleaned up.
        """
        if not self.end_time: # Check that we haven't already stopped the container
            self.end_time = datetime.now()

            if self._listener_thread:
                with Client(support.conn_addr_from_container, authkey = support.conn_key) as conn:
                    conn.send(Message.STOP)
                    self._listener_thread.join()

            self._stop_container()

            for snapshot in reversed(self.undo_list): # We can't delete an image that has images based on it so go backwards
                docker_helper.client.images.remove(image = snapshot.image.id)

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


    def commit(self):
        """ Take a snapshot of the current state so we can use UNDO to get back to it. """
        if self.undo_enabled:
            image = self.container.commit("shell-adventure", f"undo-snapshot-{len(self.undo_list)}")
            puzzles = {p.id: p.solved for p in self.get_all_puzzles()}
            self.undo_list.append( Snapshot(image, puzzles) )

    def _load_snapshot(self, index):
        """ Loads a snapshot by its index in undo_list. Deletes all images ahead of the snapshot. """
        if index == -1: return # Top of stack is current state
        snapshot = self.undo_list[index]

        self._stop_container()

        for snap_to_del in reversed(self.undo_list[index + 1:]): # Remove snapshots ahead of this one
            docker_helper.client.images.remove(image = snap_to_del.image.id)
        self.undo_list = self.undo_list[:index + 1]

        # Restart the tutorial. This will loose any running processes, and state in the tutorial. However, the only state we actually need
        # is the puzzle list.
        self._start_container(snapshot.image)

        tmp_tree = PuzzleTree("", dependents=self.puzzles) # Put puzzles under a dummy node so we can iterate  it.
        self._conn_to_container.send((Message.RESTORE, {
            "home": self.home,
            "user": self.user,
            "puzzles": [pt.puzzle for pt in tmp_tree],
        }))
        self._recv() # Wait until complete

        # Set the puzzle solved state
        for puzzle, solved in zip(self.get_all_puzzles(), snapshot.puzzles_solved.values()): # The lists are in the same order
            puzzle.solved = solved

    def can_undo(self):
        """ Returns true if can undo at least once, false otherwise. """
        return len(self.undo_list) > 1 and self.undo_enabled

    def undo(self):
        """ Undo the last step the student entered. Does nothing if there is nothing to undo. """
        if self.can_undo(): # The top image is current state
            self._load_snapshot(-2) # Top of stack is current state

    def restart(self):
        """ Restart the tutorial to its initial state. Does not regenerate the puzzles. """
        if self.can_undo():
            self._load_snapshot(0)


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
        (solved, feedback) = self._recv()
        puzzle.solved = solved

        # Update latest snapshot
        if len(self.undo_list) > 0:
            self.undo_list[-1].puzzles_solved[puzzle.id] = solved

        return (solved, feedback)

    def get_student_cwd(self) -> PurePosixPath:
        """ Get the path to the students current directory/ """
        self._conn_to_container.send( (Message.GET_STUDENT_CWD,) )
        return self._recv()

    def get_files(self, folder: PurePosixPath) -> List[Tuple[bool, bool, PurePosixPath]]:
        """
        Returns the children of the given folder in the docker container as a list of (is_dir, is_symlink, path) tuples.
        Folder should be an absolute path.
        """
        assert folder.is_absolute()

        self._conn_to_container.send( (Message.GET_FILES, folder) )
        return self._recv()

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


class Snapshot:
    """ Represents a snapshot of the state of the tutorial, so we can restore it during undo. """
    def __init__(self, image: Image, puzzles_solved: Dict[str, bool]):
        self.image = image # Docker image
        self.puzzles_solved = puzzles_solved # {puzzle_id: solved} # We need to undo solving a puzzle
