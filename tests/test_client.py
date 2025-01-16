import pytest
from unittest import mock

from utils import MockReader, MockWriter, run_threaded_client, run_server, DEFAULT_CONFIG

from netframe import Client, Message


@mock.patch("netframe.client_worker.asyncio.open_connection")
def test_send_after_conn_lost(mock_open_connection):
    msg = Message()
    reader = MockReader(ConnectionResetError())
    mock_open_connection.return_value = (reader, MockWriter())

    with run_threaded_client() as client:
        client._connLost.wait()
        with pytest.raises(RuntimeError):
            client.send(msg)


@mock.patch("netframe.client_worker.asyncio.open_connection")
def test_read_after_conn_lost(mock_open_connection):
    msg1 = Message(hdr=Message.Header(id=1, size=1), payload=bytearray(b'\x01'))
    msg2 = Message(hdr=Message.Header(id=2, size=1), payload=bytearray(b'\x02'))
    reader = MockReader(msg1.pack(), msg2.pack(), ConnectionResetError())
    mock_open_connection.return_value = (reader, MockWriter())

    with run_threaded_client() as client:
        client._connLost.wait()
        assert client.recv() == msg1
        assert client.recv() == msg2
        with pytest.raises(RuntimeError):
            client.recv()


def test_unexpected_shutdowns():
    with run_server(DEFAULT_CONFIG):
        client = Client()
        client.shutdown()

        client.connect(DEFAULT_CONFIG.ip, DEFAULT_CONFIG.port)
        client.shutdown()
        client.shutdown()