import os
import sys
import time
import multiprocessing

from netframe import Server, Connection, OwnedMessage, Config, ServerApp, ContextT
from protocol import PROTOCOL, fs_add, fs_del, fs_get, fs_get_resp, fs_list_resp, fs_ack


class App(ServerApp):
    def __init__(self, context: ContextT):
        self.storageLock = context['lock']
        self.storagePath = context['path']

        self.handlers = { 
            getattr(PROTOCOL, f"{cmd.upper()}") : getattr(self, f"handle_{cmd}")
            for cmd in ["add", "del", "get", "list"]
            if hasattr(PROTOCOL, f"{cmd.upper()}") and hasattr(self, f"handle_{cmd}")
        }


    def on_client_connect(self, client: Connection) -> bool:
        print(f"\n[{os.getpid()}]Client connected from {client.addr()}")
        return True


    def on_client_disconnect(self, client: Connection):
        print(f"[{os.getpid()}]Client from {client.addr()} disconnected")


    def on_message(self, msg: OwnedMessage):
        defaultHandler = lambda msg: msg.owner.shutdown()
        handler = self.handlers.get(msg.msg.hdr.id, defaultHandler)
        handler(msg)
        

    def handle_add(self, msg: OwnedMessage):
        req = fs_add()
        req.unpack(msg.msg)

        resp = fs_ack()
        resp.rc = fs_ack.RC.FILE_EXISTS

        path = os.path.join(self.storagePath, req.filename)
        with self.storageLock:
            if not os.path.exists(path):
                with open(path, 'wb') as file:
                    file.write(req.file)
                resp.rc = fs_ack.RC.OK

        msg.owner.send(resp.pack())


    def handle_del(self, msg: OwnedMessage):
        req = fs_del()
        req.unpack(msg.msg)
        
        resp = fs_ack()
        resp.rc = fs_ack.RC.FILE_NOT_FOUND

        path = os.path.join(self.storagePath, req.filename)
        with self.storageLock:
            if os.path.exists(path):
                os.remove(path)
                resp.rc = fs_ack.RC.OK

        msg.owner.send(resp.pack())


    def handle_get(self, msg: OwnedMessage):
        req = fs_get()
        req.unpack(msg.msg)

        path = os.path.join(self.storagePath, req.filename)
        with self.storageLock:
            if os.path.exists(path):
                resp = fs_get_resp()
                resp.filename = req.filename
                with open(path, 'rb') as file:
                    resp.file = file.read()
            else:
                resp = fs_ack()
                resp.rc = fs_ack.RC.FILE_NOT_FOUND

        msg.owner.send(resp.pack())


    def handle_list(self, msg: OwnedMessage):
        resp = fs_list_resp()

        with self.storageLock:
            for filename in os.listdir(self.storagePath):
                path = os.path.join(self.storagePath, filename)
                resp.filenameToSize[filename] = os.path.getsize(path)

        msg.owner.send(resp.pack())


if __name__ == "__main__":
    # create folder 'storage', if already exists - clear it 
    path = os.path.join(sys.path[0], 'storage')
    if os.path.exists(path):
        for filename in os.listdir(path):
            filePath = os.path.join(path, filename)
            os.remove(filePath)
    else:
        os.makedirs(path)

    context = ContextT()
    context['lock'] = multiprocessing.Lock()
    context['path'] = path

    config = Config(App, context, workerNum=4)
    server = Server(config)
    server.start()

    while True:
        time.sleep(1)