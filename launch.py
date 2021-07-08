import sys
from textwrap import indent
from shell_adventure.gui.main import ShellAdventureGUI
from shell_adventure.host_side.tutorial import Tutorial
from shell_adventure.shared.tutorial_errors import *

if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit("No tutorial config file given.")

    try:
        tutorial = Tutorial(sys.argv[1])
    except ConfigError as e:
        exit(e)
    
    def log_and_exit(header: str, message, show_logs: bool = True):
        """ Print a header, error and exit. Optionally print container logs. """
        print(f"\n\n{f' {header} '.center(60, '=')}\n")
        print(message)
        if show_logs and tutorial.logs():
            print("Container Logs:\n" + indent(tutorial.logs(), "  "))
        exit(1)

    try:
        with tutorial: # Sets up the container with the tutorial inside, context manager will remove container
            tutorial.attach_to_shell()
            gui = ShellAdventureGUI(tutorial, restart_callback = tutorial.attach_to_shell)
    except (ConfigError, ContainerStartupError) as e: # Bash session hasn't started so we don't need to show header
        exit(e)
    except ContainerError as e: # ContainerError has container logs already, so don't print them twice
        log_and_exit("An error occurred", e, show_logs = False) 
    except UnhandledError as e: # Our code in the container broke
        log_and_exit("An unhandled error occurred in the container", format_exc(e))
    except TutorialError as e: # User caused errors or environment errors
        log_and_exit("An error occurred", e)
    except Exception as e: # Our code broke
        log_and_exit("An unhandled error occurred", format_exc(e))
    finally:
        print() # Add newline so that the terminal's next program is on a line by itself properly.