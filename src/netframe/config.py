from __future__ import annotations

import socket

from typing import Callable, Any, TYPE_CHECKING
from multiprocessing import cpu_count

from netframe.message import OwnedMessage

if TYPE_CHECKING:
    from netframe.connection import Connection

ContextT = dict[str, Any]

class Config:
    def __init__(self, addr: str = socket.gethostbyname(socket.gethostname()),
                       port: int = 54314,
                       workerNum: int = cpu_count()-1,
                       gracefulShutdownTimeout: float = 5) -> None:
        self.context: ContextT = ContextT()

        self.addr = addr
        self.port = port
        
        self.workerNum: int = workerNum

        self.gracefulShutdownTimeout: float = gracefulShutdownTimeout

        self._on_client_connect: Callable[[Connection, ContextT], bool] = lambda _, __: True
        self._on_client_disconnect: Callable[[Connection, ContextT], None] = lambda _, __: None
        self._on_message: Callable[[OwnedMessage, ContextT], None] = lambda _, __: None


    def on_client_connect(self, handler: Callable[[Connection, ContextT], bool]) -> Callable[[Connection, ContextT], bool]:
        self._on_client_connect = handler
        return handler


    def on_client_disconnect(self, handler: Callable[[Connection, ContextT], None]) -> Callable[[Connection, ContextT], None]:
        self._on_client_disconnect = handler
        return handler


    def on_message(self, handler: Callable[[OwnedMessage, ContextT], None]) -> Callable[[OwnedMessage, ContextT], None]:
        self._on_message = handler
        return handler