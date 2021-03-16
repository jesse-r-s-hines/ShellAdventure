import sys, os, subprocess
from pathlib import Path
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial

def start_bash(container, name):
    """
    Starts a bash session in the docker container in a detached process. The process in the container will have the given name.
    Returns the exec process.
    """
    # docker exec the unix exec bash built-in which lets us change the name of the process
    return subprocess.Popen(["docker", "exec", "-it", container.id, "bash", "-c", f"exec -a {name} bash"])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    os.system('cls' if os.name == 'nt' else 'clear') # clear the terminal

    with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
        bash = start_bash(tutorial.container, "shell_adventure_bash")
        tutorial.connect_to_shell("shell_adventure_bash")
        gui = GUI(tutorial)

    print("\n") # Add some newlines so that the terminal's next program is on a line by itself properly.