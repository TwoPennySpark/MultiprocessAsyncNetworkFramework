import pytest
import struct

from netframe import Message


@pytest.mark.parametrize(
    ("dataBatch"),
    (
        (b'',),
        (0, "", 3.14),
        (2**32-1, "abc", -124450.000014),
        (-19, "тест", 0.0),
    )
)
def test_append_pop(dataBatch):
    m = Message()
    
    for data in dataBatch:
        bytes_ = b''
        if isinstance(data, int):
            bytes_ = data.to_bytes(4, 'little', signed=(data < 0))
        elif isinstance(data, float):
            bytes_ = struct.pack("d", data)
        elif isinstance(data, str):
            encData = data.encode()
            bytes_ = len(encData).to_bytes(4, 'little') + encData
        elif isinstance(data, bytes):
            bytes_ = len(data).to_bytes(4, 'little') + data
        else:
            raise ValueError
        
        m.append(bytes_)

    for data in dataBatch:
        if isinstance(data, int):
            assert data == int.from_bytes(m.pop(4), 'little', signed=(data < 0))
        elif isinstance(data, float):
            f = m.pop(8)
            assert data == struct.unpack("d", f)[0]
        elif isinstance(data, str):
            dataLen = int.from_bytes(m.pop(4), 'little')
            assert data == m.pop(dataLen).decode()
        elif isinstance(data, bytes):
            dataLen = int.from_bytes(m.pop(4), 'little')
            assert data == m.pop(dataLen)
                
    assert m._start == m.hdr.size


@pytest.mark.parametrize(
    ("msg", "packed"),
    (
        (Message(hdr=Message.Header(id=0, size=0), payload=bytearray()),       b'\x00\x00\x00\x00\x00\x00'),
        (Message(hdr=Message.Header(id=1, size=3), payload=bytearray(b'123')), b'\x01\x00\x03\x00\x00\x00123')
    )
)
def test_pack_unpack(msg: Message, packed: bytes):
    assert msg.pack() == packed

    copy = Message()
    copy.unpack(packed)

    assert copy.hdr.id == msg.hdr.id
    assert copy.hdr.size == msg.hdr.size
    assert copy.payload == msg.payload