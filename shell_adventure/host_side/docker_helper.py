"""
This module contains methods for launching the shell-adventure container.
"""
from typing import Union
import docker, deepmerge
from docker.models.images import Image
from docker.models.containers import Container
import shell_adventure

BASE_PATH = shell_adventure.PKG_PATH
client = docker.from_env()

def launch(image: Union[str, Image], **container_options) -> Container:
    """
    Launches the given container and sets it up for a Shell Adventure tutorial.
    Puts all the Shell Adventure files in a volume and sets all the other settings as needed.
    You can specify extra options which will be merged in with the default options to Container.run()
    Returns (container, volume). You can attach to the container to interact with the shell session inside.
    Make sure to clean up the container and volume when you are done with them.
    """
    container_options = deepmerge.always_merger.merge(dict(
        volumes = {
            shell_adventure.PKG_PATH: {'bind': f"/usr/local/shell_adventure", 'mode': 'ro'},
        },
        network_mode = "host",
        cap_add = [
            "CAP_SYS_PTRACE", # Allows us to call `pwdx` to get working directory of student
        ],
        tty = True,
        stdin_open = True,
        # remove = True, # Auto remove makes getting output logs difficult. Also, if the container isn't attached, the bash session won't quit
                         # which will leave the container running even with auto remove
        detach = True,
    ), container_options)

    container = client.containers.run(image, **container_options)
    return container
