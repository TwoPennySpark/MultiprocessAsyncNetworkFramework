from __future__ import annotations
from typing import Protocol, Type, Any, TYPE_CHECKING
from dataclasses import dataclass, field

import socket

from netframe.message import OwnedMessage
if TYPE_CHECKING:
    from netframe.connection import Connection

ContextT = dict[str, Any]

class ServerApp(Protocol):
    def __init__(self, context: ContextT):
        pass

    def on_client_connect(self, client: Connection) -> bool:
        return True

    def on_client_disconnect(self, client: Connection):
        pass

    def on_message(self, msg: OwnedMessage):
        pass


@dataclass
class Config:
    app: Type[ServerApp]
    context: ContextT = field(default_factory=ContextT)

    ip: str = socket.gethostbyname(socket.gethostname())
    port: int = 54314

    workerNum: int = 1