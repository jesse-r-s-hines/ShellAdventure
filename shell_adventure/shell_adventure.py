import sys
from textwrap import indent
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial
from shell_adventure_shared.tutorial_errors import *

def print_error_header(message: str):
    print(f"\n\n{f' {message} '.center(60, '=')}\n")

def print_logs(tutorial: Tutorial):
    if tutorial.logs():
        print("Container Logs:\n" + indent(tutorial.logs(), "  "))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    try:
        tutorial = Tutorial(sys.argv[1])
    except (FileNotFoundError, ConfigError) as e:
        print(e)
        exit(1)
    
    try:
        with tutorial: # Sets up the container with the tutorial inside, context manager will remove container
            tutorial.attach_to_shell()
            gui = GUI(tutorial, restart_callback = tutorial.attach_to_shell)
    except ConfigError as e: # We can get config errors when the container starts as well
        print(e)
        exit(1)
    except UnhandledError as e: # Our code in the container broke
        print_error_header("An unhandled error occurred in the container")
        print(format_exc(e))
        print_logs(tutorial)
        exit(-1)
    except TutorialError as e: # User caused errors or environment errors
        print_error_header("An error occurred")
        print(e)
        exit(2)
    except Exception as e: # Our code broke
        print_error_header("An unhandled error occurred")
        print(format_exc(e))
        print_logs(tutorial)
        exit(-1)
    finally:
        print() # Add newline so that the terminal's next program is on a line by itself properly.