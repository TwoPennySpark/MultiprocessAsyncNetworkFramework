import pytest

from netframe import Server, Client, Connection, OwnedMessage, Config, ContextT

TEST_IP = "127.0.0.1"
TEST_PORT = 50010

def default_on_client_connect(client: Connection, context: ContextT) -> bool:
    return True

def default_on_client_disconnect(client: Connection, context: ContextT):
    pass

def default_on_message(msg: OwnedMessage, context: ContextT):
    pass


@pytest.fixture()
def server(request):
    on_client_connect    = request.param[0] if request.param[0] else default_on_client_connect
    on_client_disconnect = request.param[1] if request.param[1] else default_on_client_disconnect
    on_message           = request.param[2] if request.param[2] else default_on_message

    config = Config(on_client_connect, on_client_disconnect, on_message,
                    ip=TEST_IP, port=TEST_PORT)
    server = Server(config)
    server.start()

    yield server

    server.stop()


@pytest.fixture()
def client():
    client = Client()
    client.connect(TEST_IP, TEST_PORT)
    
    yield client

    client.shutdown()