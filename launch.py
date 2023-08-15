#!/usr/bin/env python3
import sys
from textwrap import indent
from shell_adventure.gui.main import ShellAdventureGUI
from shell_adventure.gui.gui_widgets import standalone_fileselect
from shell_adventure.host_side.tutorial import Tutorial
from shell_adventure.shared.tutorial_errors import *

def launch(config_file: str):
    try:
        tutorial = Tutorial(config_file)
    except ConfigError as e:
        exit(str(e))

    def log_and_exit(header: str, message, show_logs: bool = True):
        """ Print a header, error and exit. Optionally print container logs. """
        print(f"\n\n{f' {header} '.center(60, '=')}\n")
        print(message)
        if show_logs and tutorial.logs():
            print("Container Logs:\n" + indent(tutorial.logs(), "  "))
        exit(1)

    print("Launching tutorial container...")
    try:
        with tutorial: # Sets up the container with the tutorial inside, context manager will remove container
            tutorial.attach_to_shell()
            gui = ShellAdventureGUI(tutorial, restart_callback = tutorial.attach_to_shell)
    except (ConfigError, ContainerStartupError) as e: # Bash session hasn't started so we don't need to show header
        exit(str(e))
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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        config_file = standalone_fileselect(filetypes = [("YAML", ".yml"), ("YAML", ".yaml")])
    else:
        config_file = sys.argv[1]

    if not config_file:
        exit("No tutorial config file given.")

    launch(config_file)