"""
This module contains methods for launching the shell-adventure container.
"""
from typing import Union, List, Tuple
import docker, shutil, deepmerge
from docker.models.images import Image
from docker.models.containers import Container
from tempfile import TemporaryDirectory
from pathlib import Path
import shell_adventure_docker

def launch(image: Union[str, Image], **container_options) -> Container:
    """
    Launches the given container and sets it up for a Shell Adventure tutorial.
    Puts all the Shell Adventure files in a volume and sets all the other settings as needed.
    You can specify extra options which will be merged in with the default options to Container.run()
    Returns (container, volume). You can attach to the container to interact with the shell session inside.
    Make sure to clean up the container and volume when you are done with them.
    """
    docker_path = '/usr/local/shell_adventure_docker'

    container_options = deepmerge.always_merger.merge(dict(
        volumes = {shell_adventure_docker.PKG_PATH: {'bind': docker_path, 'mode': 'ro'}},
        network_mode = "host",
        cap_add = [
            "CAP_SYS_PTRACE", # Allows us to call `pwdx` to get working directory of student
        ],
        tty = True,
        stdin_open = True,
        # remove = True, # Auto remove makes getting output logs difficult. We'll have to remove the container ourselves.
        detach = True,
    ), container_options)

    container = docker.from_env().containers.run(image, **container_options)
    return container

# def _make_volume() -> TemporaryDirectory:
#     """
#     Moves files needed into a tmp directory that we can use as a Docker volume. Returns the volume.
#     """
#     volume = TemporaryDirectory(prefix = "shell-adventure-")
#     vol_path = Path(volume.name)

#     # Copy files into the volume (we don't want to give the container access to the real files)
#     shutil.copytree(PKG.parent / "shell_adventure_docker", vol_path / "shell_adventure_docker",
#                     ignore = shutil.ignore_patterns("__pycache__"))

#     return volume