import sys, os, subprocess
from pathlib import Path
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial

def start_bash(container):
    """ Starts a bash session in the docker container in a detached process. Returns the process. """
    return subprocess.Popen(["docker", "exec", "-it", container.id, "bash"])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    os.system('cls' if os.name == 'nt' else 'clear') # clear the terminal

    with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
        bash = start_bash(tutorial.container, "bash")
        tutorial.connect_to_shell("bash")
        gui = GUI(tutorial)

    print("\n") # Add some newlines so that the terminal's next program is on a line by itself properly.