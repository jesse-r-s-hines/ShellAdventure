import sys
from textwrap import indent
from shell_adventure.host_side.gui import GUI
from shell_adventure.host_side.tutorial import Tutorial
from shell_adventure.shared.tutorial_errors import *

if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit("No tutorial config file given.")

    try:
        tutorial = Tutorial(sys.argv[1])
    except ConfigError as e:
        exit(e)
    
    def exit_and_log(message, header: str = None, ):
        """ Print error string and exit. Prints container logs and an optional header. """
        if header:
            print(f"\n\n{f' {header} '.center(60, '=')}\n")
        print(message)
        if tutorial.logs():
            print("Container Logs:\n" + indent(tutorial.logs(), "  "))
        exit(1)

    try:
        with tutorial: # Sets up the container with the tutorial inside, context manager will remove container
            tutorial.attach_to_shell()
            gui = GUI(tutorial, restart_callback = tutorial.attach_to_shell)
    except ConfigError as e: # We can get config errors when starting the container as well
        exit(e)
    except UnhandledError as e: # Our code in the container broke
        exit_and_log(format_exc(e), header = "An unhandled error occurred in the container")
    except TutorialError as e: # User caused errors or environment errors
        exit_and_log(e, header = "An error occurred")
    except Exception as e: # Our code broke
        exit_and_log(format_exc(e), header = "An unhandled error occurred")
    finally:
        print() # Add newline so that the terminal's next program is on a line by itself properly.