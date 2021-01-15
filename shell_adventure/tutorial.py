from typing import *
import sys, threading, shlex
import docker, dockerpty
from docker.models.containers import Container
from docker.client import DockerClient

class CommandOutput:
    """ Represents the output of a command. """

    """ The exit code that the command returned """
    exit_code: int
    
    """ The printed output of the command """
    output: str

    # """ Output to std error """
    # error: str

    def __init__(self, exitCode: int, output: str):
        self.exit_code = exitCode
        self.output = output

class Puzzle:
    """ Represents a single puzzle in the tutorial. """

    """ The question to be asked. """
    question: str
    
    """ The score given on success. Defaults to 1. """
    score: int

    """
    The function that will grade whether the puzzle was completed correctly or not.
    The function can take the following parameters. All parameters are optional, and order does not matter, 
    but must have the same name as listed here.
    
    output: Dict[str, CommandOutput]
        A dict of all commands entered to their outputs, in the order they were entered.
    flag: str
        If the flag parameter is present, an input dialog will be shown to the student when sumbitting a puzzle,
        and their input will be passed to this parameter.
    filesystem: FileSystem
        A frozen FileSystem object. Most methods that modify the file system will be disabled.
    """
    checker: Callable[..., Union[str,bool]] 

    def __init__(self, question: str, checker: Callable[..., Union[str,bool]] , score):
        self.question = question 
        self.score = score
        self.checker = checker

class FileSystem:
    """ Handles the docker container and the filesystem in it. """

    """ The docker daemon. """
    _client: DockerClient

    """ The docker container running the tutorial. """
    _container: Container

    def __init__(self):
        self._client = docker.from_env()
        self._container = self._client.containers.create('shell-adventure',
            command = 'tail -f /dev/null',
            tty = True,
            stdin_open = True,
            auto_remove = True,
        )

    def run_command(self, command: str) -> CommandOutput:
        """ Runs the given command in the tutorial environment. Returns a tuple containing (exit_code, output). """
        exit_code, output = self._container.exec_run(shlex.join(['/bin/bash', '-c', command]))
        return (exit_code, output.decode())

    def __del__(self):
        """ Stop the container. """
        self._container.stop(timeout = 0)


class Tutorial:
    """ Contains the information for a running tutorial. """

    def start():
        """ Starts the tutorial. """


if __name__ == "__main__":
    pass
    # fs = FileSystem()
    # fs._container.start()
  
    # dockerpty.start(client.api, container.id)