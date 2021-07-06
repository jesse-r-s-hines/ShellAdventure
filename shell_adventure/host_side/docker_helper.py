"""
This module contains methods for launching the shell-adventure container.
"""
from typing import Union
import docker, deepmerge
from docker.models.images import Image
from docker.models.containers import Container
import shell_adventure

client = docker.from_env()

def launch(image: Union[str, Image], **container_options) -> Container:
    """
    Launches the given container and sets it up for a Shell Adventure tutorial. Puts all the
    Shell Adventure files in a volume and sets all the other settings as needed. You can specify
    extra options which will be merged in with the default options to `Container.create()`. Returns
    the container. You can attach to the container to interact with the shell session inside. Make
    sure to `stop()` the container when you are done with it (it will auto-remove once stopped).
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
        # We will usually have to stop the container manually since the bash session won't quit on its own.
        # But if we don't have auto remove enabled a "Created" container will get left around that we can't remove
        auto_remove = True, 
        detach = True,
    ), container_options)

    container: Container = client.containers.create(image, **container_options)
    container.start()
    return container
