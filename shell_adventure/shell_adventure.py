import sys, textwrap
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial, TutorialError

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    try:
        # Context manager will make sure that the container is cleaned up, and will wrap any errors in TutorialError
        # so that we can see the container logs.
        with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
            tutorial.attach_to_shell()
            gui = GUI(tutorial, undo_callback = tutorial.attach_to_shell )
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