"""
Script to start the tutorial. Runs as a script, not a module.
"""
import os, sys
sys.path.insert(0, "/usr/local") # Add to path so we can reference our modules
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.permissions import change_user

tutorial = TutorialDocker()
tutorial.run()