import pytest
import asyncio
import multiprocessing

from unittest import mock

from netframe import Message
from netframe.server_worker import ServerWorker


class MockReader:
    def __init__(self, data: list[bytes | BaseException]):
        self.inData = data
        self.index = 0
        self.blockForeverEvent = asyncio.Event()

    async def readexactly(self, size: int):
        if self.index == len(self.inData):
            await self.blockForeverEvent.wait()

        if isinstance(self.inData[self.index], BaseException):
            raise self.inData[self.index]
        else:
            data = self.inData[self.index][:size]
            self.inData[self.index] = self.inData[self.index][size:]
            
            if len(self.inData[self.index]) == 0:
                self.index += 1
            
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
    

@mock.patch("netframe.server_worker.asyncio.start_server")
@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_config_cb_called(mock_win_socket_share, mock_start_server):
    stopEvent = multiprocessing.Event()

    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader([msg.pack(), asyncio.IncompleteReadError(b'', None)])

    writer = MockWriter()
    config = mock.MagicMock()
    config.gracefulShutdownTimeout = 0

    worker = ServerWorker(mock.MagicMock(), config, stopEvent)
    server = asyncio.create_task(worker._serve())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    stopEvent.set()
    await server

    config.on_client_connect.assert_called_once()
    config.on_message.assert_called_once()
    config.on_client_disconnect.assert_called_once()

    
@mock.patch("netframe.server_worker.asyncio.start_server")
@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_disconnect_cb_not_called_after_conn_reject(mock_win_socket_share, mock_start_server):
    stopEvent = multiprocessing.Event()

    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader([msg.pack(), asyncio.IncompleteReadError(b'', None)])

    writer = MockWriter()
    config = mock.MagicMock()
    config.on_client_connect.side_effect = lambda _, __ : False
    config.gracefulShutdownTimeout = 0

    worker = ServerWorker(mock.MagicMock(), config, stopEvent)
    server = asyncio.create_task(worker._serve())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    stopEvent.set()
    await server

    config.on_client_connect.assert_called_once()
    config.on_message.assert_not_called()
    config.on_client_disconnect.assert_not_called()