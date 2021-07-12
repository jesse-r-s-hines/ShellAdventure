import pytest
from shell_adventure.host_side import docker_helper
import docker, docker.errors
from .helpers import *

class TestDockerHelper:
    def test_image_not_found(self, check_containers):
        with pytest.raises(docker.errors.ImageNotFound, match = "pull access denied"):
            docker_helper.launch("doesnt-exist")

    def test_local_image(self, check_containers):
        try:
            container = docker_helper.launch("shelladventure/tests:alpine") # Image only stored locally
            assert container.image == docker_helper.client.images.get("shelladventure/tests:alpine")
        finally:
            container.stop(timeout = 0) # should autoremove

    # I'm not going to test an actual pull here as it would make the tests take forever