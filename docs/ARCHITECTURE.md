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

## Responsibility boundaries

| Layer | Owns | Does not own |
|---|---|---|
| Skill / client | User workflow, concise purpose, policy | Transport retries |
| Runtime | Identity enrichment, ledger, routing, leases, jobs | EDA semantics |
| Transport | Local/SSH delivery, framing, reconnect | Operation meaning |
| Adapter | Typed EDA capabilities, result normalization | Agent policy |
| Vendor bridge | Native API calls and EDA lifecycle | Cross-EDA governance |

## Reliability model

Delivery is at-least-once. Mutating operations therefore require an
`idempotency_key`. Durable jobs persist state before execution, expose an event
cursor, and allow clients to reconnect without restarting the EDA operation.
Resource leases carry monotonically increasing fencing tokens so a stale worker
cannot claim current ownership.

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

