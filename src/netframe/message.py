from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from netframe.connection import Connection


@dataclass
class Message:
    @dataclass
    class Header:
        id: int = 0
        size: int = 0
        HEADER_LEN: ClassVar[int] = 4

        def pack(self) -> bytes:
            return self.id.  to_bytes(2, 'little') + \
                   self.size.to_bytes(2, 'little')
        
        def unpack(self, bytes_):
            self.id   = int.from_bytes(bytes_[:2], 'little')
            self.size = int.from_bytes(bytes_[2:Message.Header.HEADER_LEN], 'little')


    hdr: Header = field(default_factory=Header)
    payload: bytes = b''

    _start: int = 0


    def append(self, data: bytes):
        self.payload += data
        self.hdr.size += len(data)


    def pop(self, length) -> bytes:
        if self._start + length > self.hdr.size:
            raise IndexError

        data = self.payload[self._start:self._start+length]
        self._start += length

        return data


    def pack(self) -> bytes:
        return self.hdr.pack() + self.payload


    def unpack(self, bytes_):
        self.hdr.unpack(bytes_)
        self.payload = bytes_[Message.Header.HEADER_LEN:]


@dataclass
class OwnedMessage:
    owner: Connection | None = None
    msg: Message = field(default_factory=Message)