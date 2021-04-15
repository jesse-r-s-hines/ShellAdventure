import sys, os, subprocess, textwrap
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial, TutorialError

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

    try:
        # Context manager will make sure that the container is cleaned up, and will wrap any errors in TutorialError
        # so that we can see the container logs.
        with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
            bash = start_bash(tutorial.container, "shell_adventure_bash")
            tutorial.connect_to_shell("shell_adventure_bash")

            gui = GUI(tutorial)
    except TutorialError as e:
        print("\n\n\n============ An error occurred in the tutorial ============")
        print("\nContainer Logs:\n" + textwrap.indent(e.container_logs, "    ") + "\n")
        raise e.__cause__ # "unwrap" the tutorial error.
    finally:
        print() # Add newline so that the terminal's next program is on a line by itself properly.