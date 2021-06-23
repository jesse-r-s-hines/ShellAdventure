""" Contains various exception classes """
import tblib.pickling_support
import textwrap, traceback

__all__ = [
    "TutorialContainerStartupError",
    "UserCodeError",
    "TutorialConfigException",
    "format_exc",
    "format_user_exc",
]

class TutorialContainerStartupError(Exception): # TODO move this class out of shell_adventure_docker?
    """ Exception for when the container and tutorial fail to start. """
    
    def __init__(self, message, container_logs = None):
        self.container_logs = container_logs
        if container_logs:
            message = message + "\n\nContainer Logs:\n" + textwrap.indent(self.container_logs, "    ")
        super().__init__(message)

class TutorialConfigException(Exception):
    """ Thrown if something is wrong with the Tutorial config. """
class UserCodeError(Exception):
    """ Class for when user supplied code such as PuzzleGenerator's and AutoGrader's throw. """

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

# Maybe allow pickling the exceptions with additional fields?
# See https://stackoverflow.com/questions/49715881/how-to-pickle-inherited-exceptions

# Need to make sure that this is called before I try to pickle any exceptions and after any exceptions are defined
tblib.pickling_support.install()
