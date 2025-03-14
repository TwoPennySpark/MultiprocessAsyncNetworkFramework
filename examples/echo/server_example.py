from netframe import Server, Connection, OwnedMessage, Config, ServerApp, ContextT

import os
import time

class App(ServerApp):
    def __init__(self, context: ContextT):
        pass

    def on_client_connect(self, client: Connection) -> bool:
        print(f"\n[{os.getpid()}]Client connected from {client.addr()}")
        return True


    def on_client_disconnect(self, client: Connection):
        print(f"[{os.getpid()}]Client from {client.addr()} disconnected")


    def on_message(self, msg: OwnedMessage):
        print(f"[{os.getpid()}]ON_MSG:", msg.msg)
        msg.owner.send(msg.msg)


if __name__ == "__main__":
    config = Config(App, workerNum=4)
    server = Server(config)
    server.start()

    # user app
    while True:
        time.sleep(1)
