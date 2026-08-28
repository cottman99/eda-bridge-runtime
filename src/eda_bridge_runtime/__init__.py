"""Agent-neutral execution runtime for EDA bridges."""

from ._version import __version__
from .adapter import Adapter, AdapterContext, AdapterResult
from .context import EDAContext
from .jobs import JobStore
from .ledger import ExecutionLedger
from .protocol import ActorIdentity, RequestEnvelope, ResponseEnvelope
from .runtime import Runtime
from .supervisor import run_job_worker, spawn_detached_worker

__all__ = [
    "__version__",
    "ActorIdentity",
    "Adapter",
    "AdapterContext",
    "AdapterResult",
    "EDAContext",
    "ExecutionLedger",
    "JobStore",
    "RequestEnvelope",
    "ResponseEnvelope",
    "Runtime",
    "run_job_worker",
    "spawn_detached_worker",
]
