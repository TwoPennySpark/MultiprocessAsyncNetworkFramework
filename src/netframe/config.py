from __future__ import annotations
from typing import Protocol, Any, TYPE_CHECKING

import socket

from netframe.message import OwnedMessage

if TYPE_CHECKING:
    from netframe.connection import Connection

ContextT = dict[str, Any]


class ServerApp(Protocol):
    def on_client_connect(self, client: Connection, context: ContextT) -> bool:
        ...

    def on_client_disconnect(self, client: Connection, context: ContextT):
        ...

    def on_message(self, msg: OwnedMessage, context: ContextT):
        ...


class Config:
    def __init__(self, app: ServerApp,
                       ip: str = socket.gethostbyname(socket.gethostname()),
                       port: int = 54314,
                       workerNum: int = 1,
                       gracefulShutdownTimeout: float = 0) -> None:
        self.context: ContextT = ContextT()
        self.app = app

        self.ip = ip
        self.port = port
        
        self.workerNum = workerNum

        self.gracefulShutdownTimeout = gracefulShutdownTimeout