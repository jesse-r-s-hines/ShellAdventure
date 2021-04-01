from typing import List
import random

class RandomHelper:
    """ RandomHelper is a class that generates random names, contents, and file paths. """

    _name_dictionary: List[str]
    """ A list of strings that will be used to generate random names. """

    def __init__(self, name_dictionary: str):
        """
        Creates a RandomHelper.
        name_dictionary is a string containing words, each on its own line.
        """
        names = set(name_dictionary.splitlines())
        names.discard("") # remove empty entries
        self._name_dictionary = list(names) # choice() only works on list.

    def name(self):
        if len(self._name_dictionary) == 0:
            raise Exception("Out of unique names.") # TODO custom exception.
        choice = random.choice(self._name_dictionary)
        self._name_dictionary.remove(choice) # We can't choose the same name again.
        return choice