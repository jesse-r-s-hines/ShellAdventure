""" Contains various exception classes that the tutorial will throw. """
import tblib.pickling_support
import textwrap, traceback

__all__ = [
    "TutorialError",
    "ContainerError",
    "ConfigError",
    "UserCodeError",
    "format_exc",
    "format_user_exc",
]

class TutorialError(Exception):
    """ Base class for exceptions thrown by the tutorial. """

class ContainerError(TutorialError): # TODO move this class out of shell_adventure_docker?
    """ Exception for when the container and tutorial fail to start. """
    
    def __init__(self, message, container_logs = None):
        self.message = message
        self.container_logs = container_logs

    def __str__(self):
        string = self.message
        if self.container_logs:
            string += "\n\nContainer Logs:\n" + textwrap.indent(self.container_logs, "  ")
        return string

    def __reduce__(self):
        # So we can pickle the exceptions, https://stackoverflow.com/questions/49715881/how-to-pickle-inherited-exceptions
        return (type(self), (self.message, self.container_logs))

class ConfigError(TutorialError):
    """ Thrown if something is wrong with the Tutorial config. """

class UserCodeError(TutorialError):
    """ Class for when user supplied code such as PuzzleGenerator's and AutoGrader's throw. """

    def __init__(self, message: str, original_exc: Exception = None):
        self.message = message
        self.original_exc = original_exc

    def __str__(self):
        string = self.message
        if self.original_exc:
            string += "\n" + textwrap.indent(format_user_exc(self.original_exc), "  ")
        return string

    def __reduce__(self):
        return (type(self), (self.message, self.original_exc))


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

# Need to make sure that this is called before I try to pickle any exceptions and after any exceptions are defined
tblib.pickling_support.install()
