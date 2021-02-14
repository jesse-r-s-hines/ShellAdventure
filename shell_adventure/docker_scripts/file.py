import pathlib

class File(pathlib.PosixPath):
    """
    File is an extention of pathlib.PosixPath, with a few convenience methods added.
    Refer to pathlib documentation at https://docs.python.org/3/library/pathlib.html
    """

    def children(self):
        """
        Return list of directory's contents. Raises "NotADirectoryError" if not a directory.
        Basically an alias of Path.iterdir() but returns a list instead of a generator.
        """
        return list(self.iterdir())
    
    def _get_path(self) -> str:
        return str(self.resolve())
    path = property(_get_path)
    """ Returns the absolute path to this file as a string. """
    
    def touch(self, mode=0o666, exist_ok=True, recursive = False):
        """
        See Path.touch(). The only difference is that it will "mkdir" missing dirs in the path if recursive is set to True.
        New directories will be made with the same mode, except with execute permissions set.
        """
        if recursive:
            self.parent.mkdir(mode = mode | 0o111, parents = True, exist_ok=True) # mkdir is already recursive
        super().touch(mode, exist_ok)
