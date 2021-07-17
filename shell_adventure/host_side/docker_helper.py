"""
This module contains methods for launching a container for the tutorial.
"""
from typing import Union
import docker, deepmerge
from docker.models.images import Image
from docker.models.containers import Container
from docker.errors import ImageNotFound
from shell_adventure.shared import messages
import shell_adventure

client = docker.from_env()

def launch(image: Union[str, Image], **container_options) -> Container:
    """
    Attempts to pull the given image if a string is given, then launches the image container and
    sets it up for a Shell Adventure tutorial. Puts all the Shell Adventure files in a volume and
    sets all the other settings as needed. You can specify extra options which will be merged in
    with the default options to `Container.create()`. Returns the container. You can attach to the
    container to interact with the shell session inside. Make sure to `stop()` the container when 
    you are done with it (it will auto-remove once stopped).
    """
    container_options = deepmerge.always_merger.merge(dict(
        volumes = {
            shell_adventure.PKG_PATH: {'bind': f"/usr/local/shell_adventure", 'mode': 'ro'},
        },
        # network_mode = "host", # network_mode host doesn't work on Docker for Windows
        # Map the port inside the container to localhost
        ports = {messages.port: ('127.0.0.1', messages.port)},
        cap_add = [
            "CAP_SYS_PTRACE", # Allows us to call `pwdx` to get working directory of student
        ],
        tty = True,
        stdin_open = True,
        # We will usually have to stop the container manually since the bash session won't quit on its own.
        # But if we don't have auto remove enabled a "Created" container will get left around that we can't remove
        auto_remove = True,
        detach = True,
    ), container_options)

    if isinstance(image, str): # Pull the image or get the image
        try:
            image = client.images.get(image)
        except ImageNotFound as e: # If we don't have a local image pull it from online
            # We don't want to pull everytime since that it is very slow, especially on Windows
            image = client.images.pull(image) # Propagate any errors 

    container: Container = client.containers.create(image, **container_options)
    container.start()
    return container
