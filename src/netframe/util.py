import os
import sys
import json
import socket
import asyncio
import pathlib
import logging.config
import logging.handlers


if sys.platform == "win32":
    def win_socket_share(sock: socket.socket) -> socket.socket:
        sockData = sock.share(os.getpid())
        return socket.fromshare(sockData)
    

def loop_policy_setup(isMultiprocess: bool):
    asyncio.set_event_loop(asyncio.new_event_loop())
    if sys.platform == "win32":
        if isMultiprocess:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else: # pragma: no cover
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