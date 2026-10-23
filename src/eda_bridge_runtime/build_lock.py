"""Crash-released local file locks for derived knowledge builds."""

import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from .errors import ExecutionError

_guard = threading.Lock()
_locks = {}
_local = threading.local()


@contextmanager
def build_lock(path: Path, *, timeout: float = 30):
    key = str(path.resolve())
    with _guard:
        lock = _locks.setdefault(key, threading.RLock())
    if not lock.acquire(timeout=timeout):
        raise ExecutionError(
            "knowledge_building", "Another process is preparing these sources", phase="knowledge"
        )
    held = getattr(_local, "held", set())
    _local.held = held
    try:
        if key in held:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as stream:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            deadline = time.monotonic() + timeout
            while True:
                try:
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ExecutionError(
                            "knowledge_building",
                            "Another process is preparing these sources",
                            phase="knowledge",
                        ) from None
                    time.sleep(0.05)
            held.add(key)
            try:
                yield
            finally:
                held.remove(key)
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)
    finally:
        lock.release()
