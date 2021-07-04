""" Run the docker_tests inside the docker container and display the output. """
import os, sys, shlex
import tests.docker_tests
from shell_adventure.host_side import docker_helper

args = sys.argv[1:]
test_dir = tests.docker_tests.__path__[0] #type: ignore
docker_test_dir = "/usr/local/shell_adventure_docker_tests"

container = docker_helper.launch("shell-adventure/tests:main",
    volumes = {
        test_dir: {'bind': docker_test_dir, 'mode': 'ro'},
    },
    working_dir = "/home/student",
)

# Disable pytest cache, since writing in a volume while root causes problems
command = ["docker", "exec", "-it", "--user", "root",  "--workdir", docker_test_dir,  container.id, "pytest", "-p", "no:cacheprovider", *args]
os.system(" ".join(map(shlex.quote, command)))
container.stop(timeout = 0)
container.remove()
