import pytest
from multiprocessing import Queue

from utils import run_server, run_client

from netframe import Server, Client, Message, OwnedMessage, Connection, Config, ContextT


def disconnect_on_client_connect(client: Connection, context: ContextT) -> bool:
    return False


def echo_on_message(msg: OwnedMessage, context: ContextT):
    msg.owner.send(msg.msg)


def send_3_then_disconnect_on_client_connect(client: Connection, context: ContextT) -> bool:
    msg = Message()

    client.send(msg)
    client.send(msg)
    client.send(msg)
    
    return False


def send_3_then_disconnect_on_message(msg: OwnedMessage, context: ContextT):
    client = msg.owner

    resp = Message()
    client.send(resp)
    client.send(resp)
    client.send(resp)
    
    client.shutdown()


# make sure that everything sent by the client won't be recieved 
# by server in case of instant rejection of client's connection
@pytest.mark.parametrize("server", (
                        (disconnect_on_client_connect, None, echo_on_message),
                        ),
                        indirect=True)
def test_instant_reject(server: Server, client: Client):
    msg = Message()
    client.send(msg)
    client.send(msg)

    with pytest.raises(RuntimeError):
        client.recv()


# make sure that everything scheduled for send by the 
# server(in on_client_connect callback) before disconection is completed
@pytest.mark.parametrize("server", (
                        (send_3_then_disconnect_on_client_connect, None, None),
                        ),
                        indirect=True)
def test_send_then_reject(server: Server, client: Client):
    client.recv()
    client.recv()
    client.recv()
    with pytest.raises(RuntimeError):
        client.recv()

        
# make sure that everything scheduled for send by the 
# server(in on_message callback) before disconection is completed
@pytest.mark.parametrize("server", (
                        (None, None, send_3_then_disconnect_on_message),
                        ),
                        indirect=True)
def test_recv_send_then_disconnect(server: Server, client: Client):
    msg = Message()
    client.send(msg)

    client.recv()
    client.recv()
    client.recv()
    with pytest.raises(RuntimeError):
        client.recv()


class App:
    def on_client_connect(self, client: Connection, context: ContextT) -> bool:
        return True

    def on_client_disconnect(self, client: Connection, context: ContextT):
        context["inQ"].put(None)

    def on_message(self, msg: OwnedMessage, context: ContextT):
        msg.owner.send(msg.msg)
        context["inQ"].put(msg.msg)


def test_client_send_completion():
    serverInQ = Queue()
    config = Config(App())
    config.context["inQ"] = serverInQ

    recvMsgNum, sendMsgNum = 0, 1024

    with run_server(config):
        with run_client() as client:
            msg = Message()
            for _ in range(sendMsgNum):
                client.send(msg)

        while serverInQ.get(timeout=5) != None:
            recvMsgNum += 1

    assert recvMsgNum == sendMsgNum