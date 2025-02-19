import pytest
from multiprocessing import Queue

from utils import run_server, run_client

from netframe import Server, Client, Message, OwnedMessage, Connection, Config, ContextT, ServerApp


class test_instant_reject_app(ServerApp):
    def __init__(self, context: ContextT): ...

    def on_client_connect(self, client: Connection) -> bool:
        return False

    def on_message(self, msg: OwnedMessage):
        msg.owner.send(msg.msg)

# make sure that everything sent by the client won't be recieved 
# by server in case of instant rejection of client's connection
@pytest.mark.parametrize("server", (test_instant_reject_app,), indirect=True)
def test_instant_reject(server: Server, client: Client):
    msg = Message()
    client.send(msg)
    client.send(msg)

    with pytest.raises(ConnectionResetError):
        client.recv()


class test_send_then_reject_app(ServerApp):
    def __init__(self, context: ContextT): ...

    def on_client_connect(self, client: Connection) -> bool:
        for _ in range(3):
            client.send(Message())

        return False

# make sure that everything scheduled for send by the 
# server(in on_client_connect callback) before disconection is completed
@pytest.mark.parametrize("server", (test_send_then_reject_app,), indirect=True)
def test_send_then_reject(server: Server, client: Client):
    for _ in range(3):
        client.recv()

    with pytest.raises(ConnectionResetError):
        client.recv()


class test_recv_send_then_disconnect_app(ServerApp):
    def __init__(self, context: ContextT): ...

    def on_message(self, msg: OwnedMessage):
        client = msg.owner
        for _ in range(3):
            client.send(Message())

        client.shutdown()
        
# make sure that everything scheduled for send by the 
# server(in on_message callback) before disconection is completed
@pytest.mark.parametrize("server", (test_recv_send_then_disconnect_app,), indirect=True)
def test_recv_send_then_disconnect(server: Server, client: Client):
    client.send(Message())

    for _ in range(3):
        client.recv()
    with pytest.raises(ConnectionResetError):
        client.recv()


class test_client_send_full_completion_app:
    def __init__(self, context: ContextT):
        self.inQ = context['inQ']

    def on_client_connect(self, client: Connection) -> bool:
        return True

    def on_client_disconnect(self, client: Connection):
        self.inQ.put(None)

    def on_message(self, msg: OwnedMessage):
        msg.owner.send(msg.msg)
        self.inQ.put(msg.msg)

# test for this issue:
# https://blog.netherlabs.nl/articles/2009/01/18/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable
def test_client_send_full_completion():
    serverInQ = Queue()
    context = {'inQ': serverInQ}
    config = Config(test_client_send_full_completion_app, context)

    recvMsgNum, sendMsgNum = 0, 1024

    with run_server(config):
        with run_client() as client:
            msg = Message()
            for _ in range(sendMsgNum):
                client.send(msg)

        while serverInQ.get(timeout=5) != None:
            recvMsgNum += 1

    assert recvMsgNum == sendMsgNum