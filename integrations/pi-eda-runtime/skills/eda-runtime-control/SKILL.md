---
name: eda-runtime-control
description: Route local or SSH EDA work through the stable EDA Bridge Runtime from Pi Agent.
---

# EDA Runtime control for Pi

Use the ten `eda_*` tools for EDA work. Do not use shell commands as an alternate EDA control
path. Every call needs one concise `purpose` explaining the immediate engineering reason.

When the pasted EDA context and the selected vendor Skill already identify the connection and
operation, call `eda_submit` directly. Do not routinely list connections, resolve context, or query
capabilities first. Use discovery only when information is genuinely missing or stale.

Use `eda_read` for an intended non-mutating operation. Runtime mechanically obtains missing safety
metadata and rejects unknown or mutating operations before execution, so the Agent should not
spend a separate turn on that preflight. Keep `eda_submit` for mutations and for calls whose
safety cannot yet be proven. If a known response is
large but the task needs only a few facts, use `result_view` with exact RFC 6901 JSON Pointers and
deterministic `value`, `count`, or `exists` modes. It is also available for terminal waits and
read-only plan steps; plan mutations reject it. Omit it for exploration and never guess paths.

When 2..16 typed operations are already decided and ordered on one connection, use one
`eda_run_plan` call. Give every step a concise purpose and every mutating step a unique stable
idempotency key. Ask Runtime to wait only when a later step depends on a durable result. Keep
single operations, open-ended diagnosis, branching judgment, and unrelated targets outside plans.

Mutating calls require a stable `idempotency_key`. Never blindly repeat a mutation after timeout or
disconnect; inspect its durable job or Run state first. `eda_connection_reset` only refreshes the
Runtime-owned transport and never closes EDA.

When a result includes an `eda-runtime.resource/v1` object, retain its release fields for the active
task and use the declared typed release operation when finished. Release only `runtime-owned`
resources. Never close, kill, or claim a reused or user-owned EDA application merely because it is
visible. If no typed Runtime route exists, record the bounded purpose, lane, reason, and outcome with
`eda-runtime audit bypass`; never store the raw command or GUI input in the ledger.

For a new `eda_read` or `eda_submit`, request its bounded `wait` option when completion is needed,
avoiding a second Agent turn. Use `eda_job_wait` to resume a job already returned to the Agent.
Use `eda_job_status` only for a single observation after reconnecting and `eda_job_events` only
when event detail is needed for diagnosis.

Treat Runtime results and audit records as execution facts. Keep customer-specific object names,
coordinates, and business rules in the task or vendor Skill, not in this shared adapter.
