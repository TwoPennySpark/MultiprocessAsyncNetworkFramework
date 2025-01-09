import pytest
import asyncio
import multiprocessing

from unittest import mock

from netframe import Message
from netframe.server_worker import ServerWorker


class MockReader:
    def __init__(self, *data: bytes | BaseException):
        self.inData = list(data)
        self.index = 0
        self.allRead = asyncio.Event()
        self.blockForever = asyncio.Event()


    async def readexactly(self, size: int) -> bytes:
        if self.index == len(self.inData):
            self.allRead.set()
            await self.blockForever.wait()

        if isinstance(self.inData[self.index], BaseException):
            exc = self.inData[self.index]

            self.index += 1
            if self.index == len(self.inData):
                self.allRead.set()

            raise exc
        else:
            data = self.inData[self.index][:size]
            self.inData[self.index] = self.inData[self.index][size:]
            
            if len(self.inData[self.index]) == 0:
                self.index += 1
                if self.index == len(self.inData):
                    self.allRead.set()
            
            return data


class MockWriter:
    def __init__(self):
        self.buffer = b''
        self.closed = False

    def write(self, data: bytes):
        assert self.closed == False
        self.buffer += data

    async def drain(self):
        pass

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass

    def is_closing(self):
        return self.closed

    def get_extra_info(self, name):
        return ('', 0)
    

@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_config_cb_called(mock_win_socket_share):
    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader(msg.pack(), asyncio.IncompleteReadError(b'', None))

    writer = MockWriter()
    config = mock.MagicMock()

    worker = ServerWorker(mock.MagicMock(), config, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))
    await reader.allRead.wait()

    config.on_client_connect.assert_called_once()
    config.on_message.assert_called_once()
    config.on_client_disconnect.assert_called_once()


@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_disconnect_cb_not_called_after_conn_reject(mock_win_socket_share):
    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader(msg.pack(), asyncio.IncompleteReadError(b'', None))

    writer = MockWriter()
    config = mock.MagicMock()
    config.on_client_connect.side_effect = lambda _, __ : False

    worker = ServerWorker(mock.MagicMock(), config, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    config.on_client_connect.assert_called_once()
    config.on_message.assert_not_called()
    config.on_client_disconnect.assert_not_called()


@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_exception_in_on_client_connect_cb(mock_win_socket_share):
    reader = MockReader()
    writer = MockWriter()
    config = mock.MagicMock()
    config.on_client_connect.side_effect = lambda _, __ : 1/0

    worker = ServerWorker(mock.MagicMock(), config, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    config.on_client_connect.assert_called_once()
    assert(len(worker._connections) == 0)
    config.on_client_disconnect.assert_not_called()