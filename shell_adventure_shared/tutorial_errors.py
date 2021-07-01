""" Contains various exception classes that the tutorial will throw. """
import textwrap, traceback

__all__ = [
    "TutorialError",
    "ContainerError",
    "ContainerStartupError",
    "ContainerStoppedError",
    "ConfigError",
    "WrappedError",
    "UserCodeError",
    "UnhandledError",
    "format_exc",
    "format_user_exc",
]

class TutorialError(Exception):
    """ Base class for exceptions thrown by the tutorial. """

class ContainerError(TutorialError):
    """
    Exception for when something goes wrong in the container that we can't catch in the container side Python,
    such as the container failing to start.
    """
    
    def __init__(self, message: str, container_logs: str = ""):
        self.message: str = message
        self.container_logs: str = container_logs

    def __str__(self):
        string = self.message
        if self.container_logs.strip():
            string += "\n\nContainer Logs:\n" + textwrap.indent(self.container_logs, "  ")
        return string

    def __reduce__(self):
        # So we can pickle the exceptions, https://stackoverflow.com/questions/49715881/how-to-pickle-inherited-exceptions
        return (type(self), (self.message, self.container_logs))

class ContainerStartupError(ContainerError):
    """ Exception for when the container and tutorial fail to start. """

class ContainerStoppedError(ContainerError):
    """
    Exception for when the container stops during the tutorial without sending us an error. This will happen if something
    stops/crashes the container or the main process (such using Ctrl-D to end the shell session)
    """

class ConfigError(TutorialError):
    """ Thrown if something is wrong with the Tutorial config. """

class WrappedError(TutorialError):
    """
    Base class for an exception that is wrapping another so that we can pickle it and send it to the host.
    You can pass it a tb_str which is a string representation of the original error traceback.
    """
    # We can't send arbitrary errors and traceback info over the connection since they may not be pickleable. tblib has hacks
    # that let us send tracebacks, but we still can't guarantee that an error thrown by user created code will pickle. Also, 
    # sending the traceback object makes it so we can't see the lines of the original file since the file doesn't exist outside
    # the container. So instead we just wrap exceptions, and store the traceback in formatted string form.

    def __init__(self, message: str, tb_str: str = None):
        self.message = message
        self.tb_str = tb_str

    def __str__(self):
        string = self.message
        if self.tb_str:
            string += "\n" + textwrap.indent(self.tb_str, "  ")
        return string

    def __reduce__(self):
        return (type(self), (self.message, self.tb_str))

class UserCodeError(WrappedError):
    """ Class for when user supplied code such as PuzzleGenerator's and AutoGrader's throw. """

class UnhandledError(WrappedError):
    """
    Class for an unexpected error in our code occurs. It wrap the exception and stores the traceback as a string so
    that we can send it over the network to the host.
    """


def format_exc(e: Exception) -> str:
    """ Formats an exception with traceback. Wrapper for traceback.format_exception. """
    lines = traceback.format_exception(type(e), e, e.__traceback__)
    return "".join(lines)

def format_user_exc(e: Exception) -> str:
    """
    Format an exception in user supplied code. Filters out our code from the traceback so we
    can show only the relevant data to the user.
    """
    # See https://stackoverflow.com/questions/31949760/how-to-limit-python-traceback-to-specific-files
    frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "<string>"]
    lines = traceback.format_list(frames) + traceback.format_exception_only(type(e), e)
    
    return "Traceback (most recent call last):\n" + "".join(lines)
