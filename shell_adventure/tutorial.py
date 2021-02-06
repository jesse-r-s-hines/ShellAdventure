from typing import *
from types import ModuleType
import yaml
import importlib.util, inspect

from shell_adventure.filesystem import FileSystem
from shell_adventure.support import *

class Tutorial:
    """ Contains the information for a running tutorial. """

    _puzzle_module_inject: ClassVar[Dict[str, object]] = {
        "Puzzle": Puzzle,
    }
    """ The classes/modules/packages to inject into the puzzle generator modules. """

    config_file: Path
    """ The path to the config file for this tutorial """

    modules: Dict[str, ModuleType]
    """ Puzzle modules mapped to their name. """

    generators: Dict[str, Callable[[FileSystem], Puzzle]]
    """ All available puzzle generator functions mapped to their name. """

    class PuzzleTree:
        """ A tree node so that puzzles can be unlocked after other puzzles are solved. """
        def __init__(self, generator: str, puzzle: Puzzle = None, dependents: List[Puzzle] = None):
            self.generator = generator
            self.puzzle = puzzle
            self.dependents = dependents if dependents else []

    puzzles: List[PuzzleTree]
    """ The tree of puzzles in this tutorial. """

    file_system: FileSystem
    """ The FileSystem object containing the Docker container for the tutorial (when the tutorial is running). """

    def __init__(self, config_file: PathLike):
        self.file_system = None
        self.config_file = Path(config_file)

        # TODO add validation and error checking, document config options
        with open(config_file) as temp:
            config = yaml.safe_load(temp)

            # Load modules
            files = [PKG_DIR / "puzzles/default.py"] + config.get('modules', [])
            module_list = [self._get_module(Path(file)) for file in files]
            self.modules = {module.__name__: module for module in module_list}

            # Get puzzle generators from the modules
            self.generators = {}
            for module_name, module in self.modules.items():
                for func_name, func in inspect.getmembers(module, inspect.isfunction):
                    # Exclude imported functions, lambdas, and private functions
                    if func.__module__ == module_name and func_name != "<lambda>" and not func_name.startswith("_"):
                        self.generators[f"{module_name}.{func_name}"] = func

            self.puzzles = []
            for gen in config.get('puzzles', []):
                assert gen in self.generators, f"Unknown puzzle generator {gen}."
                self.puzzles.append(Tutorial.PuzzleTree(gen))

    def _get_module(self, file_path: Path) -> ModuleType:
        """
        Gets a module object from a file path to the module. The file path is relative to the config file.
        Injects some functions and classes into the module's namespace. TODO doc which classes and functions
        """
        if (not file_path.is_absolute()): # Files are relative to the config file
            file_path = self.config_file.parent / file_path

        module_name = file_path.stem # strip ".py"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)

        # Inject names into the modules
        for name, obj in Tutorial._puzzle_module_inject.items():
            setattr(module, name, obj)

        spec.loader.exec_module(module) # type: ignore # MyPy is confused about the types here

        return module

    def solve_puzzle(self, puzzle: Puzzle, flag: str = None) -> Tuple[bool, str]:
        """ Tries to solve the puzzle. Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded. """
        args = {
            # "output": output,
            "flag": flag,
            "file_system": self.file_system,
        }
        # Only pass the args that the checker function has
        checker_params = puzzle.get_checker_params()
        assert set(checker_params).issubset(args.keys()), 'Only paramaters, "flag", "file_system" and "output" are allowed in checker functions.'
        args = {param: args[param] for param in checker_params}

        checker_result = puzzle.checker(**args)

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

    def run(self):
        """ Starts the tutorial. """
        self.file_system = FileSystem()

        # Generate the puzzles
        for puzzle_tree in self.puzzles:
            puzzle_tree.puzzle = self.generators[puzzle_tree.generator](self.file_system)

    # def attach(self, stdout = None, stderr = None, stdin = None):
    #     """ Attaches a the container to terminal for a bash session. """
    #     dockerpty.exec_command(self.file_system.docker_client.api, self.file_system.container.id, 'bash',
    #         stdout = stdout, stderr = stderr, stdin = stdin
    #     )