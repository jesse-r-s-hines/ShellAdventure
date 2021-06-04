from __future__ import annotations
from typing import List, Tuple, Union
import random, re, lorem
from . import file as f

class RandomHelper:
    """ RandomHelper is a class that generates random names, contents, and file paths. """

    _name_dictionary: List[str]
    """ A list of strings that will be used to generate random names. """

    _content_sources: List[List[str]]
    """ The sources that will be used to generate random content. List of files, each file is a list of paragraphs. """

    # It would be more efficient to store these as tree.
    _shared_folders: List[f.File]
    """ A list of shared folders. random.folder() can use existing folders if they are shared. """

    def __init__(self, name_dictionary: str, content_sources: List[str] = []):
        """
        Creates a RandomHelper.
        name_dictionary is a string containing words, each on its own line.
        """
        names = set(name_dictionary.splitlines())
        names.discard("") # remove empty entries
        self._name_dictionary = list(names) # choice() only works on list.

        def clean_paragraph(paragraph: str) -> str:
            # paragraph = re.sub(r"\s*\n\s*", "", paragraph) # unwrap
            paragraph = paragraph.rstrip()
            paragraph = "\n".join([l for l in paragraph.split("\n") if l.strip() != ""]) # remove blank lines.
            return paragraph

        self._content_sources = []
        for source in content_sources:
            paragraphs = re.split(r"\s*\n\s*\n", source) # split into paragraphs
            paragraphs = [clean_paragraph(para) for para in paragraphs if para.strip() != ""]
            # # split paragraphs into lists of sentences
            # para_sentences = [re.findall(r".*?\.\s+", para, flags = re.DOTALL) for para in paragraphs] 
            self._content_sources.append(paragraphs)

        self._shared_folders = []

    def name(self):
        """ Returns a random word that can be used as a file name. The name is taken from the name_dictionary. """
        if len(self._name_dictionary) == 0:
            raise Exception("Out of unique names.") # TODO custom exception.
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

    def file(self, parent: f.File, ext = None) -> f.File:
        """ Creates a File with a random name. See File.rand_file() for more details. """
        parent = parent.resolve()
        ext = "" if ext == None else f".{ext}"
        new_file = f.File("/") # garanteed to exist.

        # check if file already exists. This can happen if a hardcoded name happens to match the random one.
        while new_file.exists():
            new_file = parent / f"{self.name()}{ext}"

        return new_file

    def folder(self, parent: f.File, depth: Union[int, Tuple[int, int]] = (1, 3), create_new_chance: float = 0.5) -> f.File:
        """ Makes a File to a random folder under parent. See File.random_folder() for more details. """

        if isinstance(depth, tuple): depth = random.randint(depth[0], depth[1])
        folder = parent.resolve()
        
        for i in range(depth):
            choices = [subfolder for subfolder in self._shared_folders if subfolder.parent == folder]
            if len(choices) == 0 or random.uniform(0, 1) <= create_new_chance: # Create new shared folder
                folder = self.file(folder) # create random file under folder
                self.mark_shared(folder)
            else:
                folder = random.choice(choices)

        return folder

    def mark_shared(self, folder: f.File):
        """ Marks a folder as shared. The folder does not have to exist yet. """
        if folder.exists() and not folder.is_dir():
            raise Exception(f"Can't mark {folder} as shared, it already exists as a f. Can only mark folders as shared.")
        self._shared_folders.append(folder.resolve())
