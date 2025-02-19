import pytest

from netframe import Server, Client, Config
from utils import TEST_IP, TEST_PORT


@pytest.fixture()
def server(request):
    app = request.param

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