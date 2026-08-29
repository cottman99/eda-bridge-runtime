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

After capabilities establish that an operation is non-mutating, use `eda_read`; it is the
client-visible read-only permission lane and rejects unknown or mutating operations. Keep
`eda_submit` for mutations and for calls whose safety cannot yet be proven. If a known response is
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

After a submission returns a durable `job_id`, prefer one `eda_job_wait` call over repeated status
polls. Use `eda_job_status` for a single observation after reconnecting and `eda_job_events` only
when event detail is needed for diagnosis.

Treat Runtime results and audit records as execution facts. Keep customer-specific object names,
coordinates, and business rules in the task or vendor Skill, not in this shared adapter.
