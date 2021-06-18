import sys, textwrap
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    try:
        # Context manager will make sure that the container is cleaned up
        with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
            tutorial.attach_to_shell()
            gui = GUI(tutorial, undo_callback = tutorial.attach_to_shell )
    except Exception as e:
        print("\n\n============ An error occurred in the tutorial ============")
        raise e
    finally:
        print() # Add newline so that the terminal's next program is on a line by itself properly.