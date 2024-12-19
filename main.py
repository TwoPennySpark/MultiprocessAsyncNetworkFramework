import os
import time
import threading
import signal
import asyncio
import datetime
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# def blocking_func(x):
#    time.sleep(x) # Pretend this is expensive calculations
#    return x * 5

# async def main():
#     loop = asyncio.get_running_loop()

#     # pool = multiprocessing.Pool()
#     # out = await pool.apply_async(blocking_func, args=(3,)) # This blocks the event loop.
#     executor = ProcessPoolExecutor()
#     out = await loop.run_in_executor(executor, blocking_func, 10)  # This does not
#     print(out)


class Worker:
    def __init__(self, inQ, outQ):
        self.inQ = inQ
        self.outQ = outQ


    async def wait(self):
        # threading.Thread(target=self.dequeue, daemon=True).start()

        executor = ThreadPoolExecutor(1)
        self.loop.run_in_executor(executor, self.dequeue(11111))
        # asyncio.create_task(asyncio.to_thread(self.dequeue(1)))

        # time.sleep(1)
        while True:
            print("waiting...")
            await asyncio.sleep(1)


    def enqueue(self, msg):
        print("enqueue:", msg)
        self.outQ.put(msg)


    def dequeue(self, msg):
        print(msg)
        while True:
            # print("waiting for msg...")
            msg = self.outQ.get()
            print("got msg:", msg)
            asyncio.run_coroutine_threadsafe(self.send(msg), self.loop)
            # asyncio.set_event_loop(self.loop)
            # self.loop.call_soon_threadsafe(self.send, msg)
            # self.loop.create_task(self.send(msg))


    async def send(self, msg):
        print("sending msg:", msg)
        # time.sleep(2)


    def work(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.wait())

import sys
import datetime
from threading import Thread
from multiprocessing import Process

async def keep_printing(msg):
    while True:
        if msg=="func1":
            asyncio.create_task(keep_printing("func4"))
        print(datetime.datetime.now(), msg)
        await asyncio.sleep(1)


async def main():
    asyncio.create_task(keep_printing("func1"))
    asyncio.create_task(keep_printing("func2"))
    asyncio.create_task(keep_printing("func3"))

    await asyncio.sleep(10)


def func(f):
    f()

class A:
    def dec(self, f):
        self.f = f
        return f
import functools
def start():
    # a = A()
    # @a.dec
    def f():
        print("fasdsdaad1")
    # a.f = f
    fp = functools.partial(f)
    Process(target=func, args=(f,), daemon=True).start()

    
async def app(scope, receive, send):
    # print(f"[{os.getpid()}]app")
    
    # print("SCOPE:", scope)
    event = await receive()
    print("EVENT:", event)

    if event['type'] == 'lifespan.startup':
        await send({'type': 'lifespan.startup.complete'})
    elif event['type'] == 'lifespan.shutdown':
        print("=================================================")
        await send({'type': 'lifespan.shutdown.complete'})
    else:
        response = {
            'type': 'http.response.start',
            'status': 200,
            'headers': [(b"content-type", b"text/plain")]
        }
        await send(response)

        response = {
            'type': 'http.response.body',
            'body': scope['query_string'],
            'more_body': False
        }
        await send(response)


def start_uvicorn():
    os.environ['PYTHONASYNCIODEBUG'] = '1'
    os.environ['PYTHONTRACEMALLOC'] = '1'
    # print(os.environ)

    import uvicorn
    print(f"[{os.getpid()}]main")
    uvicorn.run("main:app", port=50001, log_level="info", workers=6)
    sys.exit()

def hndl(s, frmae):
    print("hndl")


async def task111():
    print("task1")
    try:
        await asyncio.sleep(3)
    except asyncio.CancelledError:
        print("task cancelled")
        return
    print("task end")
    

async def shutdown():
    print(asyncio.current_task())
    asyncio.get_event_loop().stop()
    print("shutdown end")

class Conn:
    def __init__(self):
        self.i = 10
        print(f"[{os.getpid()}]CONN INIT")

    def __del__(self):
        print(f"[{os.getpid()}]CONN DEL")

class Temp:
    def __del__(self):
        print(f"[{os.getpid()}]Temp DEL")
        # del self.conn

    def run(self):
        print(f"[{os.getpid()}]RUN")
        self.conn = Conn()

def start(target):
    target()


if __name__ == "__main__":
    print(f"[{os.getpid()}]MAIN")
    temp = Temp()
    p = Process(target=start, args=(temp.run,), daemon=True)
    p.start()
    p.join()
    sys.exit()

    loop = asyncio.get_event_loop()
    loop.create_task(task111())
    loop.create_task(task111())
    loop.create_task(task111())
    loop.create_task(shutdown())
    # asyncio.run(watch())
    # start_uvicorn()
    loop.run_forever()

    sys.exit()

    # inQ = asyncio.Queue()
    # outQ = asyncio.Queue()
    inQ = multiprocessing.Queue()
    outQ = multiprocessing.Queue()
    worker = Worker(inQ, outQ)
    multiprocessing.Process(target=worker.work, daemon=True).start()

    count = 0
    while True:
        worker.enqueue(str(count))
        count += 1
        time.sleep(1)