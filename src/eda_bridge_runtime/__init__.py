"""Agent-neutral execution runtime for EDA bridges."""

from ._version import __version__
from .adapter import Adapter, AdapterContext, AdapterResult
from .connections import ConnectionRegistry, ConnectionSpec, discover_connection_origin
from .context import EDAContext, capability_digest, stable_origin_id
from .jobs import JobStore
from .ledger import ExecutionLedger
from .protocol import ActorIdentity, RequestEnvelope, ResponseEnvelope, project_run
from .runtime import Runtime
from .supervisor import run_job_worker, spawn_detached_worker

__all__ = [
    "__version__",
    "ActorIdentity",
    "Adapter",
    "AdapterContext",
    "AdapterResult",
    "ConnectionRegistry",
    "ConnectionSpec",
    "discover_connection_origin",
    "EDAContext",
    "capability_digest",
    "ExecutionLedger",
    "JobStore",
    "RequestEnvelope",
    "ResponseEnvelope",
    "Runtime",
    "project_run",
    "run_job_worker",
    "spawn_detached_worker",
    "stable_origin_id",
]
