import asyncio
import threading
import multiprocessing
from unittest import mock
from contextlib import contextmanager

from netframe import Server, Client, Connection, OwnedMessage, Config, ContextT, ServerApp

class MockReader:
    def __init__(self, *data: bytes | BaseException):
        self.inData = list(data)
        self.index = 0
        self.allRead, self.allReadAsync = multiprocessing.Event(), asyncio.Event()
        self.blockForever = asyncio.Event()


    async def readexactly(self, size: int) -> bytes:
        self._check_all_read()
        if self.index == len(self.inData):
            await self.blockForever.wait()

        if isinstance(self.inData[self.index], BaseException):
            exc = self.inData[self.index]

            self.index += 1
            self._check_all_read()

            raise exc
        else:
            if size > len(self.inData[self.index]):
                raise RuntimeError("Request to read an amount of data that exceeds the size of the chunk")

            data = self.inData[self.index][:size]
            self.inData[self.index] = self.inData[self.index][size:]
            
            if len(self.inData[self.index]) == 0:
                self.index += 1
                self._check_all_read()
            
            return data

    def _check_all_read(self):
        if self.index == len(self.inData):
            self.allRead.set()
            self.allReadAsync.set()


class MockWriter:
    def __init__(self):
        self.buffer = []
        self.closed = False

    def write(self, data: bytes):
        assert self.closed == False
        self.buffer += [data]

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
    

TEST_IP = "127.0.0.1"
TEST_PORT = 50010    


def default_on_client_connect(client: Connection, context: ContextT) -> bool:
    return True

def default_on_client_disconnect(client: Connection, context: ContextT):
    pass

def default_on_message(msg: OwnedMessage, context: ContextT):
    pass


class DefaulApp(ServerApp):
    def on_client_connect(self, client: Connection, context: ContextT) -> bool:
        return True

    def on_client_disconnect(self, client: Connection, context: ContextT):
        pass

    def on_message(self, msg: OwnedMessage, context: ContextT):
        pass

DEFAULT_CONFIG = Config(DefaulApp(), ip=TEST_IP, port=TEST_PORT)


def server(config: Config):
    config.ip = TEST_IP
    config.port = TEST_PORT

    server = Server(config)
    server.start()

    yield server

    server.stop()


@contextmanager
def run_server(config: Config):
    yield from server(config)


def client():
    server = Client()
    server.connect(TEST_IP, TEST_PORT)

    yield server

    server.shutdown()


@contextmanager
def run_client():
    yield from client()


@contextmanager
def run_threaded_client():
    with (mock.patch("netframe.client.Process", threading.Thread),
          mock.patch("netframe.client.socket"),
          mock.patch("multiprocessing.queues.Queue.close"),
          mock.patch("netframe.client_worker.win_socket_share")):    
        yield from client()