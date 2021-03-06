from .tutorial import Tutorial
from .permissions import change_user
import os, sys

# By default, python won't make any files writable by "other". This turns that off. This will be called in docker container
os.umask(0o000)
with change_user("student"):
    tutorial = Tutorial(sys.argv[1])
    tutorial.run()