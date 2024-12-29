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
        
        ID_FIELD_LEN: ClassVar[int] = 2
        SIZE_FIELD_LEN: ClassVar[int] = 4
        HEADER_LEN: ClassVar[int] = ID_FIELD_LEN + SIZE_FIELD_LEN

        def pack(self) -> bytes:
            return self.id.  to_bytes(self.ID_FIELD_LEN,   'little') + \
                   self.size.to_bytes(self.SIZE_FIELD_LEN, 'little')
        
        def unpack(self, bytes_: bytes):
            self.id   = int.from_bytes(bytes_[:self.ID_FIELD_LEN], 'little')
            self.size = int.from_bytes(bytes_[ self.ID_FIELD_LEN : Message.Header.HEADER_LEN], 'little')


    hdr: Header = field(default_factory=Header)
    payload: bytearray = field(default_factory=bytearray)

    _start: int = 0


    def append(self, data: bytes):
        self.payload += data
        self.hdr.size += len(data)


    def pop(self, length: int) -> bytes:
        if self._start + length > self.hdr.size:
            raise IndexError("Request to pop an amount of data that exceeds the size of the payload")

        data = self.payload[self._start:self._start+length]
        self._start += length

        return data


    def pack(self) -> bytes:
        return self.hdr.pack() + self.payload[:self.hdr.size]


    def unpack(self, bytes_: bytes):
        self.hdr.unpack(bytes_)
        self.payload = bytearray(bytes_[Message.Header.HEADER_LEN : Message.Header.HEADER_LEN + self.hdr.size])


@dataclass
class OwnedMessage:
    owner: Connection
    msg: Message = field(default_factory=Message)