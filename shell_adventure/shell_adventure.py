from typing import Any, Dict, Union, List
import docker, docker.errors
import os, sys, shutil, tempfile
import yaml
from pathlib import Path
from threading import Thread
from multiprocessing.connection import Listener 
from shell_adventure.gui import GUI
from shell_adventure.tutorial import Tutorial

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    tutorial = Tutorial(Path(sys.argv[1]))
    tutorial.run()
