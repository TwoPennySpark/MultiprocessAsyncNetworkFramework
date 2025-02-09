from netframe import Server, Connection, OwnedMessage, Config, ServerApp, ContextT

import os
import time


class App(ServerApp):
    def on_client_connect(self, client: Connection, context: ContextT) -> bool:
        print(f"\n[{os.getpid()}]Client connected from {client.addr()}", flush=True)
        return True


    def on_client_disconnect(self, client: Connection, context: ContextT):
        print(f"[{os.getpid()}]Client from {client.addr()} disconnected", flush=True)


    def on_message(self, msg: OwnedMessage, context: ContextT):
        print(f"[{os.getpid()}]ON_MSG:", msg.msg)
        msg.owner.send(msg.msg)


if __name__ == "__main__":
    config = Config(App(), workerNum=8)
    server = Server(config)
    server.start()

    # user app
    while True:
        time.sleep(1)
