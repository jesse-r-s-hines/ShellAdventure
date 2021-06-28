import sys
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial
from shell_adventure_docker.exceptions import *

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    try:
        # Context manager will make sure that the container is cleaned up
        with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
            tutorial.attach_to_shell()
            gui = GUI(tutorial, undo_callback = tutorial.attach_to_shell )
    except ConfigError as e:
        print("============ Error in tutorial configuration ============\n")
        print(e)
        exit(2)
    except TutorialError as e: # User caused errors or environment errors
        print("\n\n============ An error occurred ============\n")
        print(e)
        exit(3)
    except Exception as e: # Our code broke
        print("\n\n============ An unhandled error occurred ============\n")
        print(format_exc(e))
        exit(4)
    finally:
        print() # Add newline so that the terminal's next program is on a line by itself properly.