""" Contains various exception classes """
import tblib.pickling_support
import textwrap

__all__ = [
    "TutorialContainerStartupError",
    "UserCodeError",
    "TutorialConfigException",
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


# Need to make sure that this is called before I try to pickle any exceptions and after any exceptions are defined
tblib.pickling_support.install()
