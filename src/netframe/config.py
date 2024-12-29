from __future__ import annotations
from typing import Callable, Any, TYPE_CHECKING

import socket

from netframe.message import OwnedMessage

if TYPE_CHECKING:
    from netframe.connection import Connection

ContextT = dict[str, Any]

class Config:
    def __init__(self, on_client_connect:    Callable[[Connection,   ContextT], bool],
                       on_client_disconnect: Callable[[Connection,   ContextT], None],
                       on_message:           Callable[[OwnedMessage, ContextT], None],
                       ip: str = socket.gethostbyname(socket.gethostname()),
                       port: int = 54314,
                       workerNum: int = 1,
                       gracefulShutdownTimeout: float = 5) -> None:
        self.context: ContextT = ContextT()

        self.ip = ip
        self.port = port
        
        self.workerNum = workerNum

        self.gracefulShutdownTimeout = gracefulShutdownTimeout

        self.on_client_connect = on_client_connect
        self.on_client_disconnect = on_client_disconnect
        self.on_message = on_message