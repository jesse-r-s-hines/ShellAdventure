import pytest

from shell_adventure.host_side import docker_helper

# Defines some fixtures for use in the rest of the tests

@pytest.fixture()
def check_containers():
    """
    Checks the test doesn't leave any containers or images lying around.
    This will check will have issues if you have anything else running that might be starting
    or stopping docker containers.
    """
    # Get the number of images before we made the tutorial
    image_filter = {"reference": "shell-adventure*"}
    containers_before = set(docker_helper.client.containers.list(all = True))
    images_before = set(docker_helper.client.images.list(filters = image_filter))

    yield

    # Assert that the test cleaned up our containers
    containers_after = set(docker_helper.client.containers.list(all = True))
    extra_containers = containers_after - containers_before
    assert not extra_containers, "Containers left after test"

    images_after = set(docker_helper.client.images.list(filters = image_filter))
    extra_images = images_after - images_before
    assert not extra_images, "Images left after test"