import os
import sys
import socket
import asyncio


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