"""JSON-lines transports. SSH is delivery, not an EDA execution model."""

from __future__ import annotations

import json
import subprocess
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any, TextIO

from .protocol import HANDSHAKE_PROTOCOL, RequestEnvelope, ResponseEnvelope


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

    def _start(self) -> None:
        if self._process and self._process.poll() is None:
            return
        self._process = subprocess.Popen(  # noqa: S603
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        handshake = self._exchange({"protocol": HANDSHAKE_PROTOCOL, "versions": [1]})
        if handshake.get("protocol") != HANDSHAKE_PROTOCOL or handshake.get("selected") != 1:
            self.close()
            raise RuntimeError("runtime handshake failed")

    def _exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self._process and self._process.stdin and self._process.stdout
        self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self._process.stdin.flush()
        line = self._process.stdout.readline()
        if not line:
            error = self._process.stderr.read() if self._process.stderr else ""
            raise ConnectionError(f"runtime stdio closed: {error[-1000:]}")
        return json.loads(line)

    def request(self, request: RequestEnvelope) -> ResponseEnvelope:
        with self._lock:
            self._start()
            try:
                data = self._exchange(request.to_dict())
            except (BrokenPipeError, ConnectionError):
                self.close()
                self._start()
                data = self._exchange(request.to_dict())
            return ResponseEnvelope(**data)

    def close(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None


class SSHStdioTransport(PersistentStdioTransport):
    def __init__(
        self,
        host: str,
        remote_command: Sequence[str],
        *,
        ssh_binary: str = "ssh",
        ssh_options: Sequence[str] = (),
    ):
        if not host or host.startswith("-"):
            raise ValueError("invalid SSH host")
        command = [ssh_binary, *ssh_options, host, "--", *remote_command]
        super().__init__(command)


def serve_json_lines(
    input_stream: TextIO,
    output_stream: TextIO,
    handler: Callable[[RequestEnvelope], ResponseEnvelope],
) -> None:
    for line in input_stream:
        data = json.loads(line)
        if data.get("protocol") == HANDSHAKE_PROTOCOL:
            response: dict[str, Any] = {"protocol": HANDSHAKE_PROTOCOL, "selected": 1}
        else:
            response = handler(RequestEnvelope.from_dict(data)).to_dict()
        output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
        output_stream.flush()
