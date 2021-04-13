
from __future__ import annotations # Don't evaluate annotations until after the module is run.
from . import file
import os, stat, pwd, grp
from contextlib import contextmanager

class PermissionsGroup:
    """ Plain old data structure, contains read, write, and execute bools. """

    def __init__(self, read: bool, write: bool, execute: bool):
        self.read = read
        self.write = write
        self.execute = execute

    def __int__(self):
        return (self.read << 2) | (self.write << 1) | (self.execute)

    def __str__(self):
        return ("r" if self.read else "-") + ("w" if self.write else "-") + ("x" if self.execute else "-")

    @staticmethod
    def _from_str(mode: str) -> PermissionsGroup:
        """ Takes a string in "rwx" format """
        mode_set = set(mode)
        if len(mode_set) == len(mode) and mode_set.issubset({'r', 'w', 'x'}): # only contains rwx, and only one of each
            read = "r" in mode_set
            write = "w" in mode_set
            execute = "x" in mode_set
        else:
            raise ValueError(f'Invalid string "{mode}" for permissions, must only contain "r", "w", and/or "x"')

        return PermissionsGroup(read, write, execute)
    
    @staticmethod
    def _from_int(mode: int) -> PermissionsGroup:
        """ Takes an int and assigns lowermost 3 bits to read/write/execute """
        read = bool(mode & 0o4)
        write = bool(mode & 0o2)
        execute = bool(mode & 0o1)
        return PermissionsGroup(read, write, execute)

class LinkedPermissionsGroup(PermissionsGroup):
    """ Is linked to an actual file so you can get file permissions or modify permissions. """
    
    def _get_bit(self, mask: int) -> bool:
        """ Gets the read (0o4), write (0o2), or execute (0o1) bit. """
        mode = stat.S_IMODE(self._file.stat().st_mode)
        return bool((mode >> self._bit_shift) & mask)
    
    def _set_bit(self, mask: int, val: bool):
        """ Gets the read (0o4), write (0o2), or execute (0o1) bit. """
        mode = stat.S_IMODE(self._file.stat().st_mode)
        if val: # set bit
            mode = mode | (mask << self._bit_shift)
        else: # clear bit at mask
            mode = mode & ~(mask << self._bit_shift)
        self._file.chmod(mode)

    # MyPy fusses at overriding field with property. See https://github.com/python/mypy/issues/4125
    read = property(lambda self: self._get_bit(0o4), lambda self, val: self._set_bit(0o4, val)) #type: ignore 
    write = property(lambda self: self._get_bit(0o2), lambda self, val: self._set_bit(0o2, val)) #type: ignore
    execute = property(lambda self: self._get_bit(0o1), lambda self, val: self._set_bit(0o1, val)) #type: ignore

    def __init__(self, file: file.File, bit_shift: int):
        """
        bit_shift is the number of bits to shift to the right to get the rwx bits in the lowest position
        user: 6, group: 3, others: 0
        """
        self._file = file
        self._bit_shift = bit_shift


class Permissions:
    """
    Plain old data structure that represents basic Linux permissions, with user, group, and others sections.
    Currently doesn't include special permission bits such as the stick bit.
    """

    def __init__(self, mode: int = None, *, user: str = "", group: str = "", others: str = ""):
        """
        Create a permissions object. You can create one from an octal int, or by specifying user, group, and others
        with strings containing some combination of "rwx".
        Eg.
        >>> Permissions(0o777)
        >>> Permissions(user = "rw", group = "r", others = "")
        """
        if mode != None:
            self.user = PermissionsGroup._from_int(mode >> 6)
            self.group = PermissionsGroup._from_int(mode >> 3)
            self.others = PermissionsGroup._from_int(mode >> 0)
        else:
            self.user = PermissionsGroup._from_str(user)
            self.group = PermissionsGroup._from_str(group)
            self.others = PermissionsGroup._from_str(others)

    def __eq__(self, other) -> bool:
        """ Compare permission objects. You can also compare a permission object with its octal representation. """
        if isinstance(other, Permissions) or isinstance(other, int):
            return int(self) == int(other)
        else:
            raise NotImplementedError("You can only compare Permissions with other Permissions or with ints")

    def __int__(self):
        """ Returns the integer representation of the permissions. Ie. 0o777 """
        return (int(self.user) << 6) | (int(self.group) << 3) | (int(self.others))

    def __str__(self):
        """
        Returns the string representation of the permissions, as ls -l would.
        >>> str(Permissions(0o764))
        "rwx-rw-r--"
        """
        return str(self.user) + str(self.group) + str(self.others)

    def __repr__(self):
        return f"Permissions({oct(int(self))})"

class LinkedPermissions(Permissions):
    """ Is linked to an actual file so you get file permissions via the permissions object or modify permissions. """
    
    def __init__(self, file: file.File):
        self._file = file
        self.user = LinkedPermissionsGroup(file, 6)
        self.group = LinkedPermissionsGroup(file, 3)
        self.others = LinkedPermissionsGroup(file, 0)


@contextmanager
def change_user(user: str, group: str = None):
    """
    Changes the effective user of the process to user (by name). Group will default to the group with the same name as user.
    Use in a context manager like:
    ```
    with change_user("root"):
        # do stuff as root
    # We are back to default user.
    ```
    """
    group = group if group else user
    prev_user = os.geteuid()
    prev_group = os.getegid()

    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    os.setegid(gid)
    os.seteuid(uid)

    try:
        yield (uid, gid)
    finally: # change back to original user.
        os.setegid(prev_user)
        os.seteuid(prev_group)