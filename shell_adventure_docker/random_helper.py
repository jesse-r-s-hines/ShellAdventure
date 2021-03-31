from typing import Set
from pathlib import Path
from shell_adventure.support import PathLike
import random

class RandomHelper:
    """ RandomHelper is a class that generates random names, contents, and file paths. """

    _name_dictionary: Set[str]
    """ A set of strings that will be used to generate random names. """

    def __init__(self, name_dictionary: PathLike):
        self._name_dictionary = set( Path(name_dictionary).read_text().splitlines() )
        self._name_dictionary.discard("")

    def name(self):
        if len(self._name_dictionary) == 0:
            raise Exception("Out of unique names.") # TODO custom exception.
        choice = random.choice(self._name_dictionary)
        self._name_dictionary.remove(choice) # We can't choose the same name again.
        return choice