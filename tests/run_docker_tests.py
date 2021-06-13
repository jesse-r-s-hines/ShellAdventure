""" Run the docker_tests inside the docker container and display the output. """
import pytest
import os
from tempfile import TemporaryDirectory
import shell_adventure, shell_adventure_docker
from shell_adventure import launch_container

test_dir = shell_adventure.PKG_PATH.parent / "tests/docker_tests/"
docker_test_dir = "/usr/local/shell_adventure_docker_tests"

container = launch_container.launch("shell-adventure:tests",
    volumes = {
        test_dir: {'bind': docker_test_dir, 'mode': 'ro'},
    },
    working_dir = "/home/student",
)

# Disable pytest cache, since writing in a volume while root causes problems
os.system(f"docker exec -it --user=root --workdir={docker_test_dir} {container.id} pytest -p no:cacheprovider")
container.stop(timeout = 0)
container.remove()
