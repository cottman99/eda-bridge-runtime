# Architecture

## One execution path

An agent, CLI, MCP server, or EDA UI creates a versioned request envelope. The
runtime reads an explicit `EDA_CONTEXT` snapshot or a deterministic registered
binding, opens either a local or SSH transport, and submits the request to an
EDA adapter. A v2 Context adds bounded origin, session, target, selection,
capability, and freshness facts; v1 remains accepted. When the selected Skill
already establishes a typed operation, `eda.submit` performs routing, freshness
validation, and execution in one client call. A bounded inline wait can carry one durable read or
submission to terminal state without adding another Agent decision; persistence and polling remain
Runtime job mechanics rather than a new orchestration layer.
For an intended read, missing vendor safety metadata is acquired as an internal preflight on the
same connection. The Runtime—not the Agent—proves that the operation is non-mutating before the
vendor call, while explicit capability discovery remains available for engineering exploration.

When the Agent has already decided a short deterministic sequence,
`eda.run_plan` submits the typed steps through the same kernel and transport.
The Runtime validates every operation and mutation boundary before executing
the first change, then performs durable waits and failure stops mechanically.
This removes repeated Agent turns without moving engineering judgment into the
Runtime or creating another architecture layer.

All paths emit the same event model into one logical execution ledger:

`client -> runtime -> transport -> adapter -> vendor bridge -> EDA`

The ledger keeps declared intent separate from observed execution. Physical
client and server ledger segments may live on different hosts; `request_id`,
`run_id`, `trace_id`, sequence numbers, and event hashes make them mergeable.
Its authority begins when a client actually calls Runtime. A client that makes
no call cannot create a Runtime fact, so zero-call omissions and unsupported
success claims belong to the Agent client/evaluator (or a future Harness)
record. This is a deliberate observability boundary, not a reason for Runtime
to parse chat transcripts or infer actions that never occurred.

## Three logical responsibility domains

The system has three logical responsibility domains. Skill, MCP, transport,
and SSH are interfaces or internal modules, not additional product layers.

| Domain | Owns | Does not own |
|---|---|---|
| User and Agent | Intent, engineering judgment, concise purpose, attempted-or-omitted call record | Durable execution state |
| Runtime kernel | Identity enrichment, facts, routing, transport, leases, jobs, Run projection | EDA semantics |
| Vendor adapter and bridge | Official-runtime selection, governed native execution, certified workflows, EDA lifecycle, result normalization | Agent policy or cross-EDA governance |

The physical modules remain separable for testing. MCP and CLI are stateless
frontends to the Runtime kernel; local and SSH are interchangeable transports;
Skills are routing policy; vendor adapters preserve real EDA differences.
See [Deployment roles](DEPLOYMENT_ROLES.md) for host placement.

The optional [Bootstrap Experience Library](EXPERIENCE_LIBRARY.md) is advisory
package data beside this execution path, not a fourth responsibility domain.
Skills may consult it after version-matched official documentation. Runtime and
vendor adapters never depend on it to execute, never mutate it from a receipt,
and never infer engineering success from a technically successful call.

## Reliability model

Delivery is at-least-once. Mutating operations therefore require an
`idempotency_key`. Durable jobs persist state before execution, expose an event
cursor, and allow clients to reconnect without restarting the EDA operation.
Resource leases carry monotonically increasing fencing tokens so a stale worker
cannot claim current ownership.

Synchronous responses and durable jobs retain their existing wire formats. The
Runtime adds a compact `eda-runtime.run-view/v1` projection so clients observe
the same run identity, state, terminal flag, job identity, and path-free
evidence references without forcing ADS and AnsysEM to share one execution
implementation.
The worker ledger also exposes a bounded `eda-runtime.run-receipt/v1` lookup by
`run_id`. It returns motive, identity, state, timing, evidence references, and
content hashes while keeping the full redacted vendor response on the worker
host. Receipt lookup is observation only and cannot replay an operation.
The stable projection is defined by
[`run-receipt-v1.schema.json`](schemas/run-receipt-v1.schema.json).

## Capability growth and escape lanes

The Runtime follows the shared [EDA capability model](CAPABILITY_MODEL.md).
Vendor functionality normally grows through version-matched documentation plus
governed official native execution. High-frequency, accepted recipes may also
be advertised as certified workflows; their count is not the product's API
coverage.

If neither a matching certified workflow nor governed native execution is
available, callers may use a bounded vendor script, then bounded GUI assistance,
then a manual external action. Adapters advertise which lanes exist. Every
fallback lane must be explicit in the request and ledger.

## Privacy and retention

Structured ledger records are retained until user cleanup. Raw vendor/debug
logs are artifacts with a default seven-day retention policy. Context tokens
contain no secrets. Structured values are redacted recursively before being
written.
