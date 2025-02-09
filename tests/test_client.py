import time
import queue
import pytest

from utils import run_server, DEFAULT_CONFIG

from netframe import Server, Client, Message, OwnedMessage, ContextT


def echo_on_message(msg: OwnedMessage, context: ContextT):
    msg.owner.send(msg.msg)


def echo_delayed_on_message(msg: OwnedMessage, context: ContextT):
    time.sleep(0.5)
    msg.owner.send(msg.msg)


@pytest.mark.parametrize("server", (
                        (None, None, echo_on_message),
                        ),
                        indirect=True)
def test_basic_functionality(server: Server, client: Client):
    msg = Message()
    msg.hdr.id = 0xff
    msg.append(b"hello")

    client.send(msg)
    assert msg == client.recv()


@pytest.mark.parametrize("server", (
                        (None, None, echo_delayed_on_message),
                        ),
                        indirect=True)
def test_recv_timeout(server: Server, client: Client):
    client.send(Message())
    with pytest.raises(queue.Empty):
        client.recv(timeout=0)

    client.recv(timeout=10)


def test_misplaced_calls():
    with run_server(DEFAULT_CONFIG):
        client = Client()
        
        with pytest.raises(RuntimeError):
            client.recv()
        with pytest.raises(RuntimeError):
            client.send(Message())
        with pytest.raises(RuntimeError):
            client.shutdown()

        client.connect(DEFAULT_CONFIG.ip, DEFAULT_CONFIG.port)
        with pytest.raises(RuntimeError):
            client.connect(DEFAULT_CONFIG.ip, DEFAULT_CONFIG.port)
        client.shutdown()

        with pytest.raises(RuntimeError):
            client.shutdown()