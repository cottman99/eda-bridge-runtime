"""Agent-neutral execution runtime for EDA bridges."""

from ._version import __version__
from .adapter import Adapter, AdapterContext, AdapterResult
from .connections import ConnectionRegistry, ConnectionSpec, discover_connection_origin
from .context import EDAContext, capability_digest, stable_origin_id
from .experience_library import (
    EXPERIENCE_ASSET_SCHEMA,
    EXPERIENCE_LIBRARY_SCHEMA,
    get_experience_asset,
    list_experience_assets,
    parse_experience_asset,
    validate_compiled_shortcut_binding,
    validate_experience_asset,
    validate_experience_library,
)
from .jobs import JobStore
from .ledger import ExecutionLedger
from .live_edit import LIVE_EDIT_SCHEMA, validate_live_edit
from .native_batch import (
    NATIVE_BATCH_SCHEMA,
    OPERATION_CLASSES,
    native_batch_capability_contract,
    validate_native_batch,
    validate_python_program_policy,
)
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
    "EXPERIENCE_ASSET_SCHEMA",
    "EXPERIENCE_LIBRARY_SCHEMA",
    "get_experience_asset",
    "JobStore",
    "list_experience_assets",
    "LIVE_EDIT_SCHEMA",
    "RequestEnvelope",
    "ResponseEnvelope",
    "Runtime",
    "project_run",
    "parse_experience_asset",
    "NATIVE_BATCH_SCHEMA",
    "native_batch_capability_contract",
    "OPERATION_CLASSES",
    "validate_native_batch",
    "validate_compiled_shortcut_binding",
    "validate_experience_asset",
    "validate_experience_library",
    "validate_live_edit",
    "validate_python_program_policy",
    "run_job_worker",
    "spawn_detached_worker",
    "stable_origin_id",
]
