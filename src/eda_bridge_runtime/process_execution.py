"""Bounded, cross-platform supervision of a process created by this task."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from .cancellation import check_cancellation
from .errors import ExecutionError


def run_owned_process(
    command: Sequence[str],
    *,
    timeout: float,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    max_output_bytes: int = 1048576,
    kill_tree: bool = True,
    log_path: str | None = None,
) -> subprocess.CompletedProcess:
    options = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            cwd=cwd,
            env=env,
            **options,
        )
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                check_cancellation()
                if time.monotonic() >= deadline:
                    raise ExecutionError(
                        "execution_uncertain",
                        "Execution deadline elapsed; reconcile the target before another write",
                        uncertain=True,
                    )
                if (
                    os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size
                    > max_output_bytes
                ):
                    raise ExecutionError(
                        "output_limit",
                        "Worker output exceeded the configured bound",
                        uncertain=True,
                    )
                time.sleep(0.02)
        except BaseException:
            if process.poll() is None:
                if kill_tree and os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        check=False,
                    )
                elif kill_tree:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=10)
            raise
        finally:
            if log_path:
                destination = Path(log_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                out.seek(0)
                err.seek(0)
                destination.write_bytes(
                    out.read(max_output_bytes) + b"\n" + err.read(max_output_bytes)
                )
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(max_output_bytes + 1), err.read(max_output_bytes + 1)
        if len(stdout) + len(stderr) > max_output_bytes:
            raise ExecutionError(
                "output_limit", "Worker output exceeded the configured bound", uncertain=True
            )
        return subprocess.CompletedProcess(
            list(command),
            process.returncode,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
