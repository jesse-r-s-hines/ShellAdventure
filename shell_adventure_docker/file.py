from typing import Union
from pathlib import PosixPath
import os, shutil, shlex
from .utilities import change_user

class File(PosixPath):
    """
    File is an extention of pathlib.PosixPath, with a few convenience methods added.
    Refer to pathlib documentation at https://docs.python.org/3/library/pathlib.html
    """

    def chown(self, owner: Union[str, int] = None, group: Union[str, int] = None):
        """
        Change owner user and/or group of the given path. You do not have to `change_user` to root before using `chown`. 
        user can be a system user name or a uid; the same applies to group. At least one argument is required.
        See also os.chown(), the underlying function.
        """
        with change_user("root"): # Automatically set privilege to root.
            shutil.chown(self, owner, group)

    def chmod(self, mode: Union[str, int]):
        """
        Overrides pathlib `chmod`. You do not have to `change_user` to root before using `chmod`.
        You can pass it a mode as an int, ie. `0o777` like pathlib chmod, or you can pass it a string that the `chmod` command
        would recognize such as "u+x". See https://linux.die.net/man/1/chmod
        """
        with change_user("root"): # Automatically set privilege to root.
            if isinstance(mode, str): # Just call chmod directly instead of trying to parse the mode string ourselves.
                if not self.exists(): raise FileNotFoundError
                status = os.system(f"chmod {shlex.quote(mode)} {shlex.quote(self.path)}")
                if status != 0:
                    raise Exception(f'Invalid mode "{mode}"')
            else:
                super().chmod(mode)

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
    
    def create(self, mode=0o666, exist_ok=True, recursive = True):
        """
        Basically an alias to Path.touch(), but will "mkdir" missing dirs in the path if recursive is set to True.
        New directories will be made with the same mode, except with execute permissions set.
        """
        if recursive:
            self.parent.mkdir(mode = mode | 0o111, parents = True, exist_ok=True) # mkdir is already recursive
        self.touch(mode, exist_ok)
