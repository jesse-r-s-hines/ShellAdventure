from __future__ import annotations
from typing import Union, List, Tuple
from pathlib import PosixPath
import os, shutil, shlex
from .permissions import Permissions, LinkedPermissions, change_user
import shell_adventure_docker # For access to globals

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

    def _get_children(self) -> List[File]:
        return list(self.iterdir()) # type: ignore

    children = property(_get_children)
    """
    Return list of directory's contents. Raises "NotADirectoryError" if not a directory.
    Basically an alias of Path.iterdir() but returns a list instead of a generator.
    """
    
    def _get_path(self) -> str:
        return str(self.resolve())

    path = property(_get_path)
    """ Returns the absolute path to this file as a string. """
    
    def create(self, *, mode=0o666, exist_ok=True, recursive = True, content: str = None):
        """
        Basically an alias to Path.touch(), but will "mkdir" missing dirs in the path if recursive is set to True.
        New directories will use the default mode regardless of "mode" to match POSIX `mkdir -p` behavior.
        You can also specify a content string which will be written to the file.
        """
        if recursive:
            self.parent.mkdir(parents = True, exist_ok=True) # mkdir is already recursive
        self.touch(mode, exist_ok)
        if content != None:
            self.write_text(content)

    @property
    def permissions(self) -> Permissions:
        """ Return a Permissions object representing the permissions of this file. """
        return LinkedPermissions(self)

    @permissions.setter
    def permissions(self, val: Union[int, Permissions]):
        if isinstance(val, Permissions):
            val = int(val)
        self.chmod(val)

    def same_as(self, other: File) -> bool:
        """
        Checks if two files exist and have the same contents and permissions.
        Does not compare file names or paths.
        """
        if self.is_dir() or other.is_dir(): # is_dir won't throw if not exists
            raise IsADirectoryError("File.same_as only works on files.")
        return (
            self.exists() and other.exists() and
            self.permissions == other.permissions and
            self.read_text() == other.read_text()
        )

    def random_file(self, ext = None) -> File:
        """
        Creates a File with a random name. The file is not created on disk and is not marked as shared.
        You can pass an extension which will be added to the random name.
        Will not create a file with a name that already exists.
        """
        if (shell_adventure_docker.rand == None):
            raise Exception("Can't make random files until _random has been initialized.")
        return shell_adventure_docker.rand.file(self, ext = ext)

    def random_folder(self, depth: Union[int, Tuple[int, int]] = (1, 3), create_new_chance: float = 0.5) -> File:
        """
        Makes a File to a random folder under this file. Does not create the file on disk.
        
        The returned File can include new folders in the path with random names, and it can include existing
        folders that are "shared". Folders are only "shared" if they were created via random_folder() or explicitly
        marked shared via mark_shared().
        
        Since folders created by random_folder() can be "reused" in other calls to folder() you should not modify
        the parent folders in puzzles. This way, folders created by puzzles won't intefere with one another,
        but multiple puzzles can still be created in the same directory.

        depth: Either an int or a (min, max) tuple. The returned file will have a depth under parent within
               the given range (inclusive)
        create_new_chance: float in [0, 1]. The percentage chance that a new folder will be created even if
                           shared folders are available.

        >>> home.random_folder()
        File("/home/student/random/nested/folder")
        >>> homd.random_folder()
        File("/home/student/random/folder2")
        >>> folder = home.random_folder()
        # random_folder() doesn't create the file on disk. Use mkdir() with parents = True to make the folder.
        >>> folder.mkdir(parents = True) 
        """
        if (shell_adventure_docker.rand == None):
            raise Exception("Can't make random files until _random has been initialized.")
        return shell_adventure_docker.rand.folder(self, depth, create_new_chance)

    def mark_shared(self):
        """ Marks the a File as shared. File should be a directory, though it does not have to exist yet. """
        if (shell_adventure_docker.rand == None):
            raise Exception("Can't mark shared files until _random has been initialized.")
        shell_adventure_docker.rand.mark_shared(self)