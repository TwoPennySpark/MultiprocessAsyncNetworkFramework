import time
import multiprocessing

from typing import Callable, Any
from multiprocessing.context import Process

from netframe.util import setup_logging

multiprocessing.allow_connection_pickling()

def start(realTarget: Callable[..., Any], *args: Any):
    setup_logging()
    realTarget(*args)


class WorkerPool:
    def __init__(self, workerNum: int):
        self._workerNum = workerNum
        self._workers: list[Process] = []


    def start(self, target: Callable[..., Any], args: tuple[Any, ...]=()):
        for _ in range(self._workerNum):
            proc = Process(target=start, args=(target, *args), daemon=True)
            proc.start()

            self._workers.append(proc)


    def stop(self, timeout: float | None=None):
        '''
        Waits for processes to finish within timeout period, 
        shuts them down forcefully after timeout expires
        '''
        if timeout is None:
            for worker in self._workers:
                worker.join()
        else:
            for worker in self._workers:
                start = time.perf_counter()
                worker.join(timeout)
                end   = time.perf_counter()
                
                timeout -= end-start
                if timeout < 0: 
                    timeout = 0

            for worker in self._workers:
                if worker.is_alive():
                    worker.kill()

        self._workers.clear()


    def is_started(self) -> bool:
        return True if self._workers else False