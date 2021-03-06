from typing import Any, Dict, Union, List
import docker, docker.errors
import os, sys, shutil, tempfile
import yaml
from pathlib import Path
from threading import Thread
from multiprocessing.connection import Listener 
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial

def start_terminal(container):
    # TODO maybe launch a separate terminal if the app wasn't called in one? Clear the terminal beforehand?
    os.system(f"docker exec -it {container.id} bash")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    with Tutorial(sys.argv[1]) as tutorial: # Creates and sets up the container with the tutorial inside
        terminal_thread = Thread(target = start_terminal, args = (tutorial.container,))
        terminal_thread.start()
                    
        GUI(tutorial)