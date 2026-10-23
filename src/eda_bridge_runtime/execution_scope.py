"""Propagate worker admission through nested vendor lifecycle calls."""

from contextlib import contextmanager
from contextvars import ContextVar

_current = ContextVar("eda_execution_admission", default=None)


def current_execution():
    return _current.get()


@contextmanager
def execution_scope(admission, purpose):
    token = _current.set({"admission": admission, "purpose": purpose})
    try:
        yield
    finally:
        _current.reset(token)
