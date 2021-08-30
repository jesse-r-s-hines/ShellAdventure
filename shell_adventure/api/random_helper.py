from __future__ import annotations
from typing import List, Tuple, Union, Set
import random, re, lorem
from .file import File
from shell_adventure.shared.support import PathLike

class RandomHelper:
    """
    RandomHelper is a class that generates random names, contents, and file paths.
    You can access an instance of `RandomHelper` in puzzle modules via the `shell_adventure.api.rand()` function.
    """

    def __init__(self, name_dictionary: str, content_sources: List[str] = []):
        """
        Creates a `RandomHelper`.
        name_dictionary is a string containing words, each on its own line.
        """
        names = set(name_dictionary.splitlines())
        names.discard("") # remove empty entries

        # A list of strings that will be used to generate random names.
        self._name_dictionary: List[str] = list(names) # choice() only works on list.

        def clean_paragraph(paragraph: str) -> str:
            # paragraph = re.sub(r"\s*\n\s*", "", paragraph) # unwrap
            paragraph = paragraph.rstrip()
            paragraph = "\n".join([l for l in paragraph.split("\n") if l.strip() != ""]) # remove blank lines.
            return paragraph

        # The sources that will be used to generate random content. List of files, each file is a list of paragraphs.
        self._content_sources: List[List[str]] = []
        for source in content_sources:
            paragraphs = re.split(r"\s*\n\s*\n", source) # split into paragraphs
            paragraphs = [clean_paragraph(para) for para in paragraphs if para.strip() != ""]
            # # split paragraphs into lists of sentences
            # para_sentences = [re.findall(r".*?\.\s+", para, flags = re.DOTALL) for para in paragraphs]
            self._content_sources.append(paragraphs)

        # A set of shared folders. random._folder() can use existing folders if they are shared.
        self._shared_folders: Set[File] = set()


    def name(self) -> str:
        """ Returns a random word that can be used as a file name. The name is taken from the name_dictionary. """
        if len(self._name_dictionary) == 0:
            raise RandomHelperException("Out of unique names.")
        choice = random.choice(self._name_dictionary)
        self._name_dictionary.remove(choice) # We can't choose the same name again.
        return choice

    def paragraphs(self, count: Union[int, Tuple[int, int]] = (1, 3)) -> str:
        """
        Return a random sequence of paragraphs from the content_sources.
        If no content sources are provided or there isn't enough content to provide the size it will default to a lorem ipsum generator.

        paramaters:
            count: Either an int or a (min, max) tuple. If a tuple is given, will return a random number of paragraphs
                   in the range, inclusive.
        """
        if isinstance(count, tuple): count = random.randint(count[0], count[1])
        # filter sources too small for chosen size
        sources = [source for source in self._content_sources if count <= len(source)]

        if sources: # If we have source
            # Weight the files so all paragraphs are equally likely regardless of source
            weights = [len(source) - count + 1 for source in sources]
            [source] = random.choices(sources, k = 1, weights = weights)

            index = random.randint(0, len(source) - count)
            return "\n\n".join(source[index:index+count]) + "\n"
        else:
            return lorem.get_paragraph(count = count, sep = "\n\n") + "\n"

    # === Files ===

    def _file(self, parent: PathLike, ext = None) -> File:
        """ Creates a `File` with a random name. You should use `File.rand_file()` instead of calling this method directly. """
        parent = File(parent).resolve()
        ext = "" if ext == None else f".{ext}"
        new_file = File("/") # garanteed to exist.

        # check if file already exists. This can happen if a hardcoded name happens to match the random one.
        while new_file.exists():
            new_file = parent / f"{self.name()}{ext}"

        return new_file

    def _folder(self, parent: PathLike, depth: Union[int, Tuple[int, int]] = (1, 3), create_new_chance: float = 0.5) -> File:
        """ Makes a `File` to a random folder under parent. You should use `File.random_shared_folder()` instead of calling this method directly. """

        if isinstance(depth, tuple): depth = random.randint(depth[0], depth[1])
        folder = File(parent).resolve()

        for i in range(depth):
            if folder.exists():
                choices = [d for d in folder.iterdir() if d.is_dir() and d in self._shared_folders]
            else:
                choices = []
            # Create new shared folder if no choices or random chance succeeds.
            # Add check for 1 since uniform() is an inclusive range
            roll = random.uniform(0, 1)
            if len(choices) == 0 or create_new_chance == 1 or roll < create_new_chance:
                folder = self._file(folder) # create random file under folder
                self._mark_shared(folder)
            else:
                folder = File(random.choice(choices))

        return folder

    def _mark_shared(self, folder: PathLike):
        """ Marks a folder as shared. You should use `File.mark_shared()` instead of calling this method directly. """
        folder = File(folder)
        if folder.exists() and not folder.is_dir():
            raise RandomHelperException(f"Can't mark {folder} as shared, it already exists as a f. Can only mark folders as shared.")
        self._shared_folders.add(folder.resolve())

class RandomHelperException(Exception):
    """ Error for when the `RandomHelper` fails. """