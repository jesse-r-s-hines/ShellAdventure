"""
This script will notify the host to make a commit of the container, so we can use "undo"
Runs as a script not a module.
"""
import sys
sys.path.insert(0, "/usr/local") # Add to path so we can reference our modules
from multiprocessing.connection import Client
from shell_adventure_docker import support

# We may be called before the Tutorial has actually started up, so retry a few times
# conn = support.retry(lambda: Client(support.conn_addr_from_container, authkey = support.conn_key), tries = 20, delay = 0.2)
# conn.send(support.Message.MAKE_COMMIT)
