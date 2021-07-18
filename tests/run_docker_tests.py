""" Run the docker_tests inside the docker container and display the output. """
import os, sys, shlex, tarfile, io
import tests.docker_tests
from shell_adventure.host_side import docker_helper
import shell_adventure

options = sys.argv[1:]

test_dir = tests.docker_tests.__path__[0] #type: ignore
proj_dir = shell_adventure.PKG_PATH.parent
work_dir = "/usr/local" # Path in the container we are working in

try:
    container = docker_helper.launch("shelladventure/tests:main",
        volumes = {
            test_dir: {'bind': f"{work_dir}/tests", 'mode': 'ro'},
        },
        working_dir = "/home/student",
    )

    # Disable pytest cache, since the volume is readonly (and writing in volume while root causes problems)
    command = ["docker", "exec", "-t", "--user", "root", "--workdir", work_dir, container.id,
               "pytest", "-p", "no:cacheprovider", "--cov=shell_adventure", "--cov-report=", *options, "tests"]
    os.system(" ".join(map(shlex.quote, command)))

    # Extract the .coverage file from the container
    bytes, stat = container.get_archive(f"{work_dir}/.coverage")
    tar = tarfile.open(fileobj = io.BytesIO(b''.join(bytes)))
    tar.extract(".coverage", proj_dir)
finally:
    container.stop(timeout = 0)
