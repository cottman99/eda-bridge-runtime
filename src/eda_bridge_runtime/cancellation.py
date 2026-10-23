"""Cooperative cancellation shared by durable workers and owned subprocesses."""

from contextlib import contextmanager
from contextvars import ContextVar

from .errors import ExecutionError

_requested = ContextVar("eda_cancel_requested", default=None)


@contextmanager
def cancellation_scope(check):
    token = _requested.set(check)
    try:
        yield
    finally:
        _requested.reset(token)


def check_cancellation():
    check = _requested.get()
    if check is not None and check():
        raise ExecutionError(
            "cancellation_requested",
            "Cancellation requested; verify the target before another write",
            phase="execution",
            uncertain=True,
        )
