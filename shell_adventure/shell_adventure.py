import sys, os, subprocess, textwrap, traceback
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial, TutorialError

def start_bash(tutorial):
    """
    Starts a bash session in the docker container in a detached process. The process in the container will have the given name.
    Returns the exec process.
    """
    # docker exec the unix exec bash built-in which lets us change the name of the process
    os.system('cls' if os.name == 'nt' else 'clear') # clear the terminal
    name = "shell_adventure_bash"
    bash = subprocess.Popen(["docker", "exec", "-it", "--user", "student", tutorial.container.id, "bash", "-c", f"exec -a {name} bash"])
    tutorial.connect_to_shell(name)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    try:
        # Context manager will make sure that the container is cleaned up, and will wrap any errors in TutorialError
        # so that we can see the container logs.
        with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
            start_bash(tutorial)
            gui = GUI(tutorial, undo_callback = lambda: start_bash(tutorial) )
    except TutorialError as e:
        print("\n\n============ An error occurred in the tutorial ============")
        print("\nContainer Logs:\n" + textwrap.indent(e.container_logs, "    ") + "\n")
        if isinstance(e.__cause__, EOFError):
            # EOFError just means the connection terminated because the container failed
            # so we don't need to tell the user about that. Just print the container logs.
            sys.exit(1)
        else:
            raise e.__cause__ from None # "unwrap" the tutorial error.
    finally:
        print() # Add newline so that the terminal's next program is on a line by itself properly.