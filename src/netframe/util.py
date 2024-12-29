import os
import sys
import json
import socket
import asyncio
import pathlib
import logging.config
import logging.handlers


def win_socket_share(sock: socket.socket) -> socket.socket:
    sockData = sock.share(os.getpid())
    return socket.fromshare(sockData)
    

def loop_policy_setup(isMultiprocess: bool):
    if sys.platform == "win32":
        if isMultiprocess:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass


def setup_logging():
    config = pathlib.Path("logging/config.json")
    with open(config) as f:
        config = json.load(f)

    logging.config.dictConfig(config)