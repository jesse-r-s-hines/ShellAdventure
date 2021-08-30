from __future__ import annotations
from typing import Union, List, Tuple
from pathlib import PosixPath
import shutil, subprocess
from .permissions import Permissions, LinkedPermissions, change_user
import shell_adventure.api # For access to globals

class File(PosixPath):
    """
    File is an extention of pathlib.PosixPath, with a few convenience methods added.
    Refer to pathlib documentation at [python.org](https://docs.python.org/3/library/pathlib.html)
    """

    @classmethod
    def home(cls) -> File:
        """ Return the home directory of the student. Equivalent to the "home" parameter in puzzle templates. """
        if shell_adventure.api._home: # Get home directory from tutorial
            return shell_adventure.api._home
        else: # Default to PosixPath
            return File(PosixPath.home())


    # === Convenience Methods ===

    @property
    def children(self) -> List[File]:
        """
        A property that returns a list of directory's contents. Raises `NotADirectoryError` if not a directory.
        Basically an alias of `Path.iterdir()` but returns a list instead of a generator.
        """
        return list(self.iterdir()) # type: ignore

    @property
    def path(self) -> str:
        """ A property that returns the absolute path to this file as a string. """
        return str(self.resolve())

    def create(self, *, mode: int = None, exist_ok = True, recursive = True, content: str = None) -> File:
        """
        An combined version of `Path.mkdir()`, `Path.touch()`, `Path.chmod()` and `Path.write_text()`. It
        will `mkdir` missing dirs in the path if recursive is True (the default). New directories will use
        the default mode regardless of the `mode` parameter to match POSIX `mkdir -p` behavior. You can also
        specify a content string which will be written to the file.

        Returns self.
        """
        if recursive:
            self.parent.mkdir(parents = True, exist_ok = True) # mkdir is already recursive
        self.touch(exist_ok = exist_ok)
        if mode != None:
            self.chmod(mode) # touch(mode=) combines with umask first which results in odd behavior
        if content != None:
            self.write_text(content)

        return self

    # === Permissions ===

    def chown(self, owner: Union[str, int] = None, group: Union[str, int] = None):
        """
        Change owner and/or group of the given path. Automatically runs as root, you do not have to use `change_user()`
        before using `chown()`. user can be a system user name or a uid; the same applies to group. At least one
        argument is required. See also `os.chown()`, the underlying function.
        """
        with change_user("root"): # Automatically set privilege to root.
            shutil.chown(self, owner, group)

    def chmod(self, mode: Union[str, int]):
        """
        Overrides `Path.chmod()`. Automatically runs as root, you do not have to `change_user()` before using
        `chmod()`. You can pass it a mode as an int, ie. `0o777` like `Path.chmod()`, or you can pass it a string
        that the unix `chmod` command would recognize such as `"u+x"`. See the [chmod man page](https://linux.die.net/man/1/chmod)
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
    def permissions(self) -> LinkedPermissions:
        """
        A property that returns a `Permissions` object representing the permissions of this file.
        Eg.
        >>> File("A.py").permissions.user.execute
        True
        """
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
        Creates a `File` with a random name under self. The source for random names comes from the `name_dictionary` option
        in the Tutorial config. The file is not created on disk and is not marked as shared. To create the file on disk
        call `File.create()` or `mkdir()` on the file returned by `random_file()`. You can pass an extension which will be added
        to the random name. Will not create a file with a name that already exists.
        """
        return shell_adventure.api.rand()._file(self, ext = ext)

    def random_shared_folder(self, depth: Union[int, Tuple[int, int]] = (1, 3), create_new_chance: float = 0.5) -> File:
        """
        Makes a `File` to a random folder under this file. The folder may be several levels deep, and its parents may or may
        not exist. Its does not create the file or any parents on disk.

        The returned `File` can include new folders in the path with random names, and it can include existing folders that are
        "shared". Folders are only "shared" if they were created via `random_shared_folder()` or explicitly marked shared via
        `mark_shared()`.

        Folders created by `random_shared_folder()` can be "reused" in other calls to `folder()`, so you should not modify
        the folders in puzzles. This way, folders created by puzzles won't interfere with one another, but multiple puzzles can
        still be created in the same directory. If you need a folder at a random location that won't have any other puzzles put
        in it you should explicitly create a folder under the one returned by `random_shared_folder()` with something like
        >>> home.random_shared_folder().random_file().mkdir()

        depth: Either an int or a (min, max) tuple. Specifies the depth under parent of the returned file. If a tuple is given
               a random depth in rand [min, max] will be used.
        create_new_chance: float in [0, 1]. The percentage chance that a new folder will be created even if shared folders are
                           available. 0 means it will only choose existing folders unless there are none, 1 means it will only
                           create new folders.

        >>> home = File("/home/student")
        >>> home.random_shared_folder()
        File("/home/student/random/nested/folder")
        >>> home.random_shared_folder()
        File("/home/student/apple/banana")
        >>> folder.mkdir(parents = True) # random_shared_folder() doesn't create the file on disk. Use mkdir() with parents = True to make the folder.
        >>> # Make a random nested folder, but make the last folder not "shared" so we can safely rm it
        >>> home.random_shared_folder().random_file().mkdir()
        File("/home/student/orange/lime/tomato")
        >>> home.random_shared_folder(create_new_chance = 0) # Will choose an existing "shared" folder
        File("/home/student/orange/lime")
        >>> File("/").random_shared_folder(depth = [5, 6]) # Create a folder 5 or 6 levels under root
        File("/blueberry/lemon/watermellon/kiwi/strawberry")
        """
        return shell_adventure.api.rand()._folder(self, depth, create_new_chance)

    def mark_shared(self):
        """ Marks the a `File` as shared. `File` should be a directory, though it does not have to exist yet. """
        shell_adventure.api.rand()._mark_shared(self)