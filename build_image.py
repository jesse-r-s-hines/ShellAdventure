#!/usr/bin/env python3
from shell_adventure.host_side import docker_helper
import shell_adventure

PROJ_PATH = shell_adventure.PKG_PATH.parent

def build_image():
    (image, log) = docker_helper.client.images.build(
        path = str(PROJ_PATH / "docker_image"),
        dockerfile = "Dockerfile",
        tag = f"shelladventure/shell-adventure:v1.0",
        rm = True, # Remove intermediate containers
    )
    image.tag(f"shelladventure/shell-adventure:latest")

if __name__ == '__main__':
    print("Building...")
    build_image()
    print("Done!")