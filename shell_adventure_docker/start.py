"""
Script to start the tutorial. Runs as a script, not a module.
"""
import sys
sys.path.insert(0, "/usr/local") # Add to path so we can reference our modules
from importlib.util import find_spec
from shell_adventure_shared.support import sentence_list

# Check the the container has the python libraries we need.
deps = {
    # import_name: pip_package_name
    "dill": "dill",
    "lorem": "python-lorem",
}

missing_deps = [pip for imp, pip in deps.items() if find_spec(imp) == None]
if missing_deps:
    print(f'Package(s) {sentence_list(missing_deps)} are not installed in the Docker image. Add the following line to your Dockerfile:')
    print(f'  python3 -m pip --no-cache-dir install {", ".join(missing_deps)}')
    sys.exit(1)


from shell_adventure_docker.tutorial_docker import TutorialDocker

tutorial = TutorialDocker()
tutorial.run()