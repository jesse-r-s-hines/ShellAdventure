"""
This script will notify the host to make a commit of the container, so we can use "undo"
"""
from multiprocessing.connection import Client
from . import support

conn = Client(support.conn_addr_from_container, authkey = support.conn_key)
conn.send(support.Message.MAKE_COMMIT)
