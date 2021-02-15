from typing import Any, Dict, Union, List
import docker, docker.errors, dockerpty
import sys, shutil, tempfile
import yaml, json
from pathlib import Path

# TODO add tests when I have more logic in this function
def parse_config(config_file: Path) -> Dict[str, Any]:
    """ Parses and validate the given YAML file. """
    # TODO add validation and error checking, document config options
    with open(config_file) as temp:
        config = yaml.safe_load(temp)
        config["modules"] = config.get("modules", [])
    return config

def launch_container(config_file, command: Union[List[str], str] = None, resources: List[Path] = None):
    """
    Reads the config file, launches the container, and moves the files for the tutorial into the container.
    By default launches the tutorial. You can specify the command directly for tests.
    """
    if not command:
        command = ["python3", "-m", "shell_adventure.gui", "/tmp/shell-adventure/config.json"]
    if not resources: resources = []

    config = parse_config(config_file)

    with tempfile.TemporaryDirectory(prefix="shell-adventure-") as volume:
        volume = Path(volume)

        # Gather puzzle modules and put them in container volume
        (volume / "modules").mkdir()
        for module in config.pop("modules"):
            # Files are relative to the config file (if module is absolute, Path will use that, if relative it will join with first)
            module = Path(config_file.parent, module)
            dest = volume / "modules" / module.name
            if dest.exists():
                raise Exception(f"Two puzzle modules with name {module.name} found.")
            shutil.copyfile(module, dest) # Copy to volume

        # TODO add this to config file
        (volume / "resources").mkdir()
        for resource in resources:
            dest = volume / "resources" / resource.name
            shutil.copyfile(resource, dest) # Copy to volume

        # Write the config file into docker container (as json)
        Path(volume, "config.json").write_text(json.dumps(config))

        # Start the container
        docker_client = docker.from_env()

        # TODO display settings are platform dependent, so I need to adjust for that.
        # See https://medium.com/better-programming/running-desktop-apps-in-docker-43a70a5265c4
        container = docker_client.containers.run('shell-adventure',
            # user = "root",
            # Make a volume to share our puzzle files with the container.
            volumes = {volume: {'bind': '/tmp/shell-adventure', 'mode': 'rw'}},
            network_mode = "host",
            environment = {
                "PYTHONPATH": "/usr/local/",
                "DISPLAY": ":0",
            },
            command = command,

            tty = True,
            stdin_open = True,
            remove = True,
            detach = True,
        )
        logs = container.attach(stdout=True, stderr=True, stream = True, logs = True)
        try:
            dockerpty.exec_command(docker_client.api, container.id, "bash")
        except:
            pass
        print("\n".join([l.decode() for l in logs]))

        # try:
        #   # Make container. I can use this code once If got a terminal running inside docker, and don't have to detach
        # except docker.errors.ContainerError as e:
        #     print(f"Docker container failed with exit code {e.exit_status}. Output was:\n")
        #     print(e.stderr.decode().strip())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    launch_container(Path(sys.argv[1]))