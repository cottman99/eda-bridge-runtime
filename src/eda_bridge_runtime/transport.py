"""JSON-lines transports. SSH is delivery, not an EDA execution model."""

from __future__ import annotations

import contextlib
import json
import os
import queue
import shlex
import signal
import subprocess
import threading
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable, Sequence
from typing import Any, TextIO

from .protocol import HANDSHAKE_PROTOCOL, RequestEnvelope, ResponseEnvelope, new_id


class Transport(ABC):
    @abstractmethod
    def request(self, request: RequestEnvelope) -> ResponseEnvelope:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class LocalTransport(Transport):
    def __init__(self, handler: Callable[[RequestEnvelope], ResponseEnvelope]):
        self.handler = handler

    def request(self, request: RequestEnvelope) -> ResponseEnvelope:
        return self.handler(request)

    def close(self) -> None:
        return None


class PersistentStdioTransport(Transport):
    """One persistent child process for many requests, avoiding per-call startup."""

    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 30):
        self.command = list(command)
        self.timeout_seconds = timeout_seconds
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str | None] = queue.Queue()
        self._stderr_tail: deque[str] = deque(maxlen=40)

    def _start(self) -> None:
        if self._process and self._process.poll() is None:
            return
        process_group: dict[str, Any]
        if os.name == "nt":
            process_group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            process_group = {"start_new_session": True}
        self._process = subprocess.Popen(  # noqa: S603
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            **process_group,
        )
        self._stdout_queue = queue.Queue()
        self._stderr_tail = deque(maxlen=40)
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        try:
            handshake = self._exchange({"protocol": HANDSHAKE_PROTOCOL, "versions": [1]})
        except Exception:
            self.close()
            raise
        if handshake.get("protocol") != HANDSHAKE_PROTOCOL or handshake.get("selected") != 1:
            self.close()
            raise RuntimeError("runtime handshake failed")

    def _read_stdout(self) -> None:
        assert self._process and self._process.stdout
        for line in self._process.stdout:
            self._stdout_queue.put(line)
        self._stdout_queue.put(None)

    def _read_stderr(self) -> None:
        assert self._process and self._process.stderr
        for line in self._process.stderr:
            self._stderr_tail.append(line.rstrip())

    def _exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self._process and self._process.stdin
        self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self._process.stdin.flush()
        try:
            line = self._stdout_queue.get(timeout=self.timeout_seconds)
        except queue.Empty as exc:
            raise TimeoutError(
                f"runtime stdio timed out after {self.timeout_seconds:g} seconds"
            ) from exc
        if not line:
            error = "\n".join(self._stderr_tail)
            raise ConnectionError(f"runtime stdio closed: {error[-1000:]}")
        return json.loads(line)

    def request(self, request: RequestEnvelope) -> ResponseEnvelope:
        with self._lock:
            self._start()
            try:
                data = self._exchange(request.to_dict())
            except (BrokenPipeError, ConnectionError) as exc:
                self.close()
                if request.is_mutating:
                    raise ConnectionError(
                        "connection was lost during a mutating request; query with the same "
                        "idempotency key instead of blindly replaying it"
                    ) from exc
                self._start()
                data = self._exchange(request.to_dict())
            return ResponseEnvelope(**data)

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return

        # EOF is the normal shutdown contract for both a local JSON-lines worker
        # and ``ssh <host> <bridge> runtime serve``.  Give that path a short chance
        # before terminating the isolated process tree.  A bounded close keeps an
        # MCP reset or server shutdown from hanging on an uncooperative child.
        if process.stdin is not None:
            with contextlib.suppress(OSError):
                process.stdin.close()
        if self._wait(process, timeout=0.75):
            return
        self._terminate_process_tree(process)

    @staticmethod
    def _wait(process: subprocess.Popen[str], *, timeout: float) -> bool:
        try:
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False

    @classmethod
    def _terminate_process_tree(cls, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            try:
                subprocess.run(  # noqa: S603
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
            cls._wait(process, timeout=0.75)
            return

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        if cls._wait(process, timeout=0.75):
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        cls._wait(process, timeout=0.75)


class SSHStdioTransport(PersistentStdioTransport):
    def __init__(
        self,
        host: str,
        remote_command: Sequence[str],
        *,
        ssh_binary: str = "ssh",
        ssh_options: Sequence[str] = (),
        timeout_seconds: float = 30,
    ):
        if not host or host.startswith("-"):
            raise ValueError("invalid SSH host")
        command = [ssh_binary, *ssh_options, host, shlex.join(remote_command)]
        super().__init__(command, timeout_seconds=timeout_seconds)


def serve_json_lines(
    input_stream: TextIO,
    output_stream: TextIO,
    handler: Callable[[RequestEnvelope], ResponseEnvelope],
) -> None:
    for line in input_stream:
        data: dict[str, Any] = {}
        try:
            loaded = json.loads(line)
            if not isinstance(loaded, dict):
                raise ValueError("runtime frame must be a JSON object")
            data = loaded
            if data.get("protocol") == HANDSHAKE_PROTOCOL:
                versions = data.get("versions", [])
                response: dict[str, Any] = {
                    "protocol": HANDSHAKE_PROTOCOL,
                    "selected": 1 if 1 in versions else None,
                }
            else:
                response = handler(RequestEnvelope.from_dict(data)).to_dict()
        except Exception as exc:
            response = ResponseEnvelope(
                request_id=str(data.get("request_id") or new_id("req")),
                run_id=str(data.get("run_id") or new_id("run")),
                status="failed",
                error={"code": type(exc).__name__, "message": str(exc)[:500]},
            ).to_dict()
        output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
        output_stream.flush()
