from __future__ import annotations
from typing import Protocol, Any, TYPE_CHECKING
from dataclasses import dataclass, field

import socket

from netframe.message import OwnedMessage

if TYPE_CHECKING:
    from netframe.connection import Connection

ContextT = dict[str, Any]

class ServerApp(Protocol):
    def on_client_connect(self, client: Connection, context: ContextT) -> bool:
        return True

    def on_client_disconnect(self, client: Connection, context: ContextT):
        ...

    def on_message(self, msg: OwnedMessage, context: ContextT):
        ...


@dataclass
class Config:
    app: ServerApp
    context: ContextT = field(default_factory=ContextT)

    ip: str = socket.gethostbyname(socket.gethostname())
    port: int = 54314

    workerNum: int = 1
    gracefulShutdownTimeout: float | None = None