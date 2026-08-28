# Architecture

## One execution path

An agent, CLI, MCP server, or EDA UI creates a versioned request envelope. The
runtime resolves an explicit `EDA_CONTEXT/v1` token or a deterministic local
binding, opens either a local or SSH transport, and submits the request to an
EDA adapter. The adapter translates typed capabilities to the vendor bridge.

All paths emit the same event model into one logical execution ledger:

`client -> runtime -> transport -> adapter -> vendor bridge -> EDA`

The ledger keeps declared intent separate from observed execution. Physical
client and server ledger segments may live on different hosts; `request_id`,
`run_id`, `trace_id`, sequence numbers, and event hashes make them mergeable.

## Three logical responsibility domains

The system has three logical responsibility domains. Skill, MCP, transport,
and SSH are interfaces or internal modules, not additional product layers.

| Domain | Owns | Does not own |
|---|---|---|
| User and Agent | Intent, engineering judgment, concise purpose | Durable execution state |
| Runtime kernel | Identity enrichment, facts, routing, transport, leases, jobs, Run projection | EDA semantics |
| Vendor adapter and bridge | Typed EDA capabilities, native API calls, EDA lifecycle, result normalization | Agent policy or cross-EDA governance |

The physical modules remain separable for testing. MCP and CLI are stateless
frontends to the Runtime kernel; local and SSH are interchangeable transports;
Skills are routing policy; vendor adapters preserve real EDA differences.
See [Deployment roles](DEPLOYMENT_ROLES.md) for host placement.

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

## Escape lanes

The preferred path is a typed adapter capability. If unavailable, callers may
use a verified native API, then a bounded script, then bounded GUI assistance,
then a manual external action. Adapters advertise which lanes exist. Every
non-typed lane must be explicit in the request and ledger.

## Privacy and retention

Structured ledger records are retained until user cleanup. Raw vendor/debug
logs are artifacts with a default seven-day retention policy. Context tokens
contain no secrets. Structured values are redacted recursively before being
written.
