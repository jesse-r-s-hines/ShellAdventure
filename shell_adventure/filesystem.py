import shlex
import docker
from docker.models.containers import Container
from docker.client import DockerClient

from shell_adventure.support import *

class FileSystem:
    """ Handles the docker container and the file system in it. """

    docker_client: DockerClient
    """ The docker daemon. """

    container: Container
    """ The docker container running the tutorial. """

    def __init__(self):
        self.docker_client = docker.from_env()
        self.container = self.docker_client.containers.run('shell-adventure',
            # Keep the container running so we can exec into it.
            # We could run the bash session directly, but then we'd have to hide the terminal until after puzzle generation finishes.
            command = 'sleep infinity',
            tty = True,
            stdin_open = True,
            auto_remove = True,
            detach = True,
        )

    def run_command(self, command: str) -> CommandOutput:
        """ Runs the given command in the tutorial environment. Returns a tuple containing (exit_code, output). """
        exit_code, output = self.container.exec_run(f'/bin/bash -c {shlex.quote(command)}')
        return CommandOutput(exit_code, output.decode())

    def stop(self):
        """ Stops the container. """
        self.container.stop(timeout = 0)

    # TODO Move this into a context manager, or make the container run the bash command directly so that it quits when the session quits.
    def __del__(self):
        if hasattr(self, "container"):
            self.stop()