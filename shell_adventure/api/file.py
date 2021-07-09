from __future__ import annotations
from typing import Union, List, Tuple
from pathlib import PosixPath
import shutil, subprocess
from .permissions import Permissions, LinkedPermissions, change_user
import shell_adventure.api # For access to globals

class File(PosixPath):
    """
    File is an extention of pathlib.PosixPath, with a few convenience methods added.
    Refer to pathlib documentation at https://docs.python.org/3/library/pathlib.html
    """

    @classmethod
    def home(cls):
        """ Return the home directory of the student. """
        if shell_adventure.api._tutorial: # Get home directory from tutorial
            return shell_adventure.api._tutorial.home
        else: # Default to PosixPath
            return PosixPath.home()


    # === Convenience Methods ===

    @property
    def children(self) -> List[File]:
        """
        Return list of directory's contents. Raises `NotADirectoryError` if not a directory.
        Basically an alias of `Path.iterdir()` but returns a list instead of a generator.
        """
        return list(self.iterdir()) # type: ignore
    
    @property
    def path(self) -> str:
        """ Returns the absolute path to this file as a string. """
        return str(self.resolve())

    def create(self, *, mode = 0o666, exist_ok = True, recursive = True, content: str = None):
        """
        An combined version of `Path.mkdir()`, `Path.touch()`, and `Path.write_text()`. It will `mkdir`
        missing dirs in the path if recursive is True (the default). New directories will use the default
        mode regardless of the `mode` parameter to match POSIX `mkdir -p` behavior. You can also specify
        a content string which will be written to the file.

        Returns the file.
        """
        if recursive:
            self.parent.mkdir(parents = True, exist_ok = True) # mkdir is already recursive
        self.touch(mode, exist_ok)
        if content != None:
            self.write_text(content)

        return self

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


    # === Permissions ===

    def chown(self, owner: Union[str, int] = None, group: Union[str, int] = None):
        """
        Change owner and/or group of the given path. Automatically runs as root, you do not have to `change_user`
        before using `chown`. user can be a system user name or a uid; the same applies to group. At least one
        argument is required. See also `os.chown()`, the underlying function.
        """
        with change_user("root"): # Automatically set privilege to root.
            shutil.chown(self, owner, group)

    def chmod(self, mode: Union[str, int]):
        """
        Overrides `Path`'s `chmod`. Automatically runs as root, you do not have to `change_user` before using
        `chmod`. You can pass it a mode as an int, ie. `0o777` like pathlib chmod, or you can pass it a string
        that the unix `chmod` command would recognize such as "u+x". See https://linux.die.net/man/1/chmod
        """
        with change_user("root"): # Automatically set privilege to root.
            if isinstance(mode, str): # Just call chmod directly instead of trying to parse the mode string ourselves.
                if not self.exists(): raise FileNotFoundError
                process = subprocess.run(["chmod", mode, self.path])
                if process.returncode != 0:
                    raise ValueError(f'Invalid mode "{mode}"')
            else:
                super().chmod(mode)

    @property
    def permissions(self) -> Permissions:
        """ Return a Permissions object representing the permissions of this file. """
        return LinkedPermissions(self)

    @permissions.setter
    def permissions(self, val: Union[int, Permissions]):
        """ Set this `File`'s permissions. """
        if isinstance(val, Permissions):
            val = int(val)
        self.chmod(val)


    # === Randomization ===

    def random_file(self, ext = None) -> File:
        """
        Creates a File with a random name under self. The source for random names comes from the `name_dictionary` option
        in the Tutorial config. The file is not created on disk and is not marked as shared. To create the file on disk
        call `create()` or `mkdir()` on the file returned by `random_file()`. You can pass an extension which will be added
        to the random name. Will not create a file with a name that already exists.
        """
        return shell_adventure.api.rand().file(self, ext = ext)

    def random_folder(self, depth: Union[int, Tuple[int, int]] = (1, 3), create_new_chance: float = 0.5) -> File:
        """
        Makes a File to a random folder under this file. Does not create the file or any parents on disk.
        
        The returned File can include new folders in the path with random names, and it can include existing
        folders that are "shared". Folders are only "shared" if they were created via `random_folder()` or explicitly
        marked shared via `mark_shared()`.
        
        Folders created by `random_folder()` can be "reused" in other calls to `folder()`, so you should not modify
        the folders in puzzles. This way, folders created by puzzles won't interfere with one another,
        but multiple puzzles can still be created in the same directory. If you need a folder at a random location
        that won't have any other puzzles put in it you should explicitly create a folder under the one returned by
        `random_folder()` with something like
        >>> home.random_folder().random_file().mkdir()
        
        depth: Either an int or a (min, max) tuple. The returned file will have a depth under parent within
              the given range (inclusive)
        create_new_chance: float in [0, 1]. The percentage chance that a new folder will be created even if
                           shared folders are available. 0 means it will only choose existing folders, 1 means
                           it will only create new folders.

        >>> home.random_folder()
        File("/home/student/random/nested/folder")
        >>> homd.random_folder()
        File("/home/student/random/folder2")
        >>> folder = home.random_folder()
        # random_folder() doesn't create the file on disk. Use mkdir() with parents = True to make the folder.
        >>> folder.mkdir(parents = True) 
        """
        return shell_adventure.api.rand().folder(self, depth, create_new_chance)

    def mark_shared(self):
        """ Marks the a File as shared. File should be a directory, though it does not have to exist yet. """
        shell_adventure.api.rand().mark_shared(self)