import pytest
import asyncio
import multiprocessing

from unittest import mock

from utils import MockReader, MockWriter

from netframe import Message
from netframe.server_worker import ServerWorker
    

@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_config_cb_called(mock_win_socket_share):
    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader(msg.pack(), asyncio.IncompleteReadError(b'', None))

    writer = MockWriter()
    config = mock.MagicMock()

    worker = ServerWorker(mock.MagicMock(), config, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))
    await reader.allReadAsync.wait()

    config.app.on_client_connect.assert_called_once()
    config.app.on_message.assert_called_once()
    config.app.on_client_disconnect.assert_called_once()


@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_disconnect_cb_not_called_after_conn_reject(mock_win_socket_share):
    msg = Message(Message.Header(id=0, size=4), payload=bytearray(b'0'*4))
    reader = MockReader(msg.pack(), asyncio.IncompleteReadError(b'', None))

    writer = MockWriter()
    config = mock.MagicMock()
    config.app.on_client_connect.side_effect = lambda _, __ : False

    worker = ServerWorker(mock.MagicMock(), config, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    config.app.on_client_connect.assert_called_once()
    config.app.on_message.assert_not_called()
    config.app.on_client_disconnect.assert_not_called()


@mock.patch("netframe.server_worker.win_socket_share")
@pytest.mark.asyncio
async def test_exception_in_on_client_connect_cb(mock_win_socket_share):
    reader = MockReader()
    writer = MockWriter()
    config = mock.MagicMock()
    config.app.on_client_connect.side_effect = lambda _, __ : 1/0

    worker = ServerWorker(mock.MagicMock(), config, multiprocessing.Event())
    await asyncio.create_task(worker._process_new_connection(reader, writer))

    config.app.on_client_connect.assert_called_once()
    assert(len(worker._connections) == 0)
    config.app.on_client_disconnect.assert_not_called()