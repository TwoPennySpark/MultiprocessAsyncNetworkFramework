from __future__ import annotations
from typing import Callable, Any, TYPE_CHECKING

from netframe.message import OwnedMessage

if TYPE_CHECKING:
    from netframe.connection import Connection


class Config:
    def __init__(self) -> None:
        self.context = dict['str', Any]()

        self.isExternalMsgProcess: bool = False

        self._on_client_connect: Callable[[Connection], bool] = lambda _: True
        self._on_client_disconnect: Callable[[Connection], None] = lambda _: None
        self._on_message: Callable[[OwnedMessage], None] = lambda _: None


    def on_client_connect(self, handler: Callable[[Connection], bool]) -> Callable[[Connection], bool]:
        self._on_client_connect = handler
        return handler


    def on_client_disconnect(self, handler: Callable[[Connection], None]) -> Callable[[Connection], None]:
        self._on_client_disconnect = handler
        return handler


    def on_message(self, handler: Callable[[OwnedMessage], None]) -> Callable[[OwnedMessage], None]:
        self._on_message = handler
        return handler