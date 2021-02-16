# TODO rename this file?
import os, pwd, grp

def change_user(user: str, group: str = None):
    """
    Changes the effective user of the process to user (by name). Group will default to the group with the same name as user.
    Use in a context manager like:
    
    with change_user("root"):
        # do stuff as root
    We are back to default user.
    """
    return _ChangeUserContextManager(user, group)

class _ChangeUserContextManager:
    def __init__(self, user: str, group: str = None):
        self.user = user
        self.group = group if group else user
        self.prev_user = None; self.prev_group = None

    def __enter__(self):
        """ Enter the context mangaer. Returns the (uid, gid) set. """
        self.prev_user = os.geteuid()
        self.prev_group = os.getegid()

        uid = pwd.getpwnam(self.user).pw_uid
        gid = grp.getgrnam(self.group).gr_gid
 
        os.setegid(gid)
        os.seteuid(uid)

        return (uid, gid)

    def __exit__(self, type, value, traceback):
        os.setegid(self.prev_user)
        os.seteuid(self.prev_group)

