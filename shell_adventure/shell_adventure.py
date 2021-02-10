from typing import Any, Dict
import docker, docker.errors, dockerpty
import sys, tempfile, yaml, json
from pathlib import Path

# TODO add tests when I have more logic in this function
def parse_config(config_file: Path) -> Dict[str, Any]:
    """ Parses and validate the given YAML file. """
    # TODO add validation and error checking, document config options
    with open(config_file) as temp:
        config = yaml.safe_load(temp)
        config["modules"] = config.get("modules", [])
    return config

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    config_file = Path(sys.argv[1])
    config = parse_config(config_file)
    
    with tempfile.TemporaryDirectory(prefix="shell-adventure-") as volume:
        # Gather puzzle modules and put them in container volume
        for module_path in config.pop("modules"):
            # Files are relative to the config file (if module_path is absolute, Path will use that, if relative it will join with first)
            module_path = Path(config_file.parent, module_path)
            dest = Path(volume, module_path.name)
            if dest.exists():
                raise Exception(f"Two puzzle modules with name {module_path.name} found.")
            dest.write_text(module_path.read_text()) # Copy to volume
        
        # Write the config file into docker container
        Path(volume, "config.json").write_text(json.dumps(config))

        # Start the container
        docker_client = docker.from_env()

        # TODO display settings are platform dependent, so I need to adjust for that.
        # See https://medium.com/better-programming/running-desktop-apps-in-docker-43a70a5265c4
        container = docker_client.containers.run('shell-adventure',
            command=["python3", "-m", "shell_adventure.gui", "/tmp/shell-adventure/config.json"],
            # Make a volume to share our puzzle files with the container.
            volumes = {volume: {'bind': '/tmp/shell-adventure', 'mode': 'rw'}},
            network_mode = "host",
            environment = {
                "PYTHONPATH": "/usr/local/",
                "DISPLAY": ":0",
            },
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
        #   # Make container. I can use this code once I've got a terminal running inside docker, and don't have to detach
        # except docker.errors.ContainerError as e:
        #     print(f"Docker container failed with exit code {e.exit_status}. Output was:\n")
        #     print(e.stderr.decode().strip())
