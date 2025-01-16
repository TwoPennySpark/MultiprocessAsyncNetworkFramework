import pytest

from netframe import Server, Client, Config
from utils import TEST_IP, TEST_PORT, DefaulApp


@pytest.fixture()
def server(request):
    app = DefaulApp()

    if request.param[0]: app.on_client_connect    = request.param[0]
    if request.param[1]: app.on_client_disconnect = request.param[1]
    if request.param[2]: app.on_message           = request.param[2]

    config = Config(app, ip=TEST_IP, port=TEST_PORT)
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