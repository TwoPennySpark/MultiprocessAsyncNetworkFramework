import pytest
import asyncio
import multiprocessing

from unittest import mock

from utils import MockReader, MockWriter

from netframe import Message
from netframe.server_worker import ServerWorker
    

@pytest.mark.asyncio
async def test_config_cb_called():
    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader(msg.pack(), asyncio.IncompleteReadError(b'', None))

    writer = MockWriter()
    app = mock.MagicMock()

    worker = ServerWorker(mock.MagicMock(), mock.MagicMock(), app, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    while len(worker._connections):
        await asyncio.sleep(0.01)

    app.on_client_connect.assert_called_once()
    app.on_message.assert_called_once()
    app.on_client_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_cb_not_called_after_conn_reject():
    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader(msg.pack(), asyncio.IncompleteReadError(b'', None))

    writer = MockWriter()
    app = mock.MagicMock()
    app.on_client_connect.side_effect = lambda _, __ : False

    worker = ServerWorker(mock.MagicMock(), mock.MagicMock(), app, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    app.on_client_connect.assert_called_once()
    app.on_message.assert_not_called()
    app.on_client_disconnect.assert_not_called()


@pytest.mark.asyncio
async def test_exception_in_on_client_connect_cb():
    reader = MockReader()
    writer = MockWriter()
    app = mock.MagicMock()
    app.on_client_connect.side_effect = lambda _, __ : 1/0

    worker = ServerWorker(mock.MagicMock(), mock.MagicMock(), app, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    app.on_client_connect.assert_called_once()
    assert(len(worker._connections) == 0)
    app.on_client_disconnect.assert_not_called()