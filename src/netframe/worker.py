from __future__ import annotations
from typing import TYPE_CHECKING

import os
import sys
import socket
import asyncio
import functools
import uuid
import signal

from contextlib import suppress
from multiprocessing import Queue
from threading import Lock

from netframe.config import Config
from netframe.connection import Connection
from netframe.message import OwnedMessage

from netframe.protocol import Protocol


class Worker:
    def run(self, listenSock: socket.socket, 
                 inQueue:  Queue[OwnedMessage], 
                 outQueue: Queue[OwnedMessage],
                 config: Config):
        self._listenSock = listenSock

        self._inQueue  = inQueue
        self._outQueue = outQueue

        self._config = config

        self.id = os.getpid()
        self._lastConnID = 0
        self._connections: dict[int, Connection] = {}
        self._connsLock = Lock()

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            sockData = self._listenSock.share(os.getpid())
            self._listenSock = socket.fromshare(sockData)

        self.loop = asyncio.get_event_loop()

        self._setup_signals()

        if self._config.isExternalMsgProcess:
            self.loop.create_task(asyncio.to_thread(self._dequeue))
        self.loop.create_task(self._start_server())
        self.loop.run_forever()


    async def _start_server(self):
        server = await asyncio.start_server(client_connected_cb=self._process_new_connection, sock=self._listenSock)
        with suppress(asyncio.CancelledError):
            async with server:
                await server.serve_forever()


    async def _process_new_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        newConn = Connection(self.id, self._lastConnID, reader, writer, self._inQueue, self._config, self)
        if self._config._on_client_connect(newConn):
            with self._connsLock:
                self._connections[self._lastConnID] = newConn
            self._lastConnID += 1
            newConn.schedule_recv()
        else:
            asyncio.create_task(newConn.shutdown())


    def _dequeue(self):
        while True:
            msg = self._outQueue.get()
            with self._connsLock:
                receiver = self._connections[msg.connId]
                self.loop.call_soon_threadsafe(functools.partial(receiver.schedule_send, msg=msg.msg))


    def del_conn(self, id):
        with self._connsLock:
            self._connections.pop(id)


    async def _shutdown(self):
        tasks = [task for task in asyncio.all_tasks() 
                 if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
    
        await asyncio.wait_for(1, asyncio.gather(*tasks))
        
        self.loop.stop()

    
    def _setup_signals(self):
        signals = [signal.SIGTERM, signal.SIGINT]

        if sys.platform == "win32":
            signals += [signal.SIGBREAK]

            async def wakeup():
                # Windows Python blocks signal handlers while the event loop is
                # waiting for I/O. Frequent wakeups keep interrupts flowing
                while not die:
                    await asyncio.sleep(1)

                asyncio.create_task(self._shutdown())

            def sig_handler(sig, frame):
                nonlocal die
                die = True

            die = False

            for s in signals:
                signal.signal(s, sig_handler)

            self.loop.create_task(wakeup())
        else:
            for s in signals:
                signal.signal(s, lambda s, f: asyncio.create_task(self._shutdown()))