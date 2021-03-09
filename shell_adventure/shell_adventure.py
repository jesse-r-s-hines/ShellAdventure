import sys, subprocess
from pathlib import Path
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial

def start_bash(container):
    """ Starts a bash session in the docker container in a detached process. Returns the process. """
    # TODO Make this cross-platform or run in the current terminal
    return subprocess.Popen(["gnome-terminal", "--", "docker", "exec", "-it", container.id, "bash"])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
        bash = start_bash(tutorial.container)
        tutorial.connect_to_bash()
        gui = GUI(tutorial)