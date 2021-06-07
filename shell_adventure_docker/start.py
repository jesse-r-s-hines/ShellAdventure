"""
Script to start the tutorial. Runs as a script, not a module.
"""
import os, sys
sys.path.insert(0, "/usr/local") # Add to path so we can reference our modules
from shell_adventure_docker.tutorial_docker import TutorialDocker
from shell_adventure_docker.permissions import change_user


# By default, python won't make any files writable by "other". This turns that off. This will be called in docker container
os.umask(0o000)
with change_user("student"):
    tutorial = TutorialDocker()
    tutorial.run()