"""
Script to start the tutorial. Runs as a script, not a module.
"""
import sys
sys.path.insert(0, "/usr/local") # Add to path so we can reference our modules
from shell_adventure_docker.tutorial_docker import TutorialDocker

tutorial = TutorialDocker()
tutorial.run()