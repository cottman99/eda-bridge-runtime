---
name: eda-runtime-control
description: Operate exact local or SSH EDA targets through the shared native execution, knowledge, durable job and evidence contracts.
---

# EDA Runtime Control

Use the installed `eda_*` tools for EDA work. Tool names use underscores in Pi. Every call includes a concise `purpose`.
Local and SSH routes use the same Worker rules. A copied `EDA_CONTEXT` identifies
the selected target; use the task's authorization rather than asking again for
ordinary authorized operations.

1. Preserve the selected installation, version, session, project and design.
   If the task and Context establish a known contract, execute directly.
   Use exact-operation capabilities only for missing or stale contract information.
2. Use version-matched official docs/examples or installed SDK signatures to resolve
   unknown API usage. Experience is optional advice. A missing wrapper, missing MD
   or failed search is not proof that the API is unavailable or unauthorized.
3. Submit official Python with `native.execute`, schema `eda.native-program/v1`.
   Choose `runtime`, `mode` and `effect` independently. Both observe and mutate
   programs use `eda_submit` and a stable `idempotency_key`; arbitrary Python never
   uses `eda_read`. Normal imports and installed SDK dependencies are available.
4. Verify the requested result using native readback, durable output or the declared
   validation program. Report execution and engineering validation separately.

GUI Context normally selects `mode: live` in that session. Choose background or
offline execution for an isolated output or a task needing those modes. The Bridge
reports which modes its backend implements. Worker admission serializes conflicting
requests across connection aliases; do not run an older writer on the same target.

`eda_read` serves registered observations such as `docs.query`, `docs.get` and
session status. Knowledge preparation is automatic and independent of execution.
Request only the evidence needed; inspect the source kind and version. If documentation
is insufficient, use a bounded native observation to inspect the installed SDK.

Accepted jobs are pending. Use bounded inline `wait` or `eda_job_wait`, then status,
events or `eda_run_get` after reconnecting. Preserve the original idempotency key.
Never replay an uncertain mutation with a new key. Cancellation uses `eda_job_cancel`;
a request to cancel an active vendor call does not prove that it stopped.

Use `eda_run_plan` for 2..16 already-decided ordered steps on one connection. Each
step needs its own purpose and each mutation a stable key. Plan views are read-only.
`result_view` uses known RFC 6901 pointers; omit it while exploring an unknown result.
Runtime wait bounds are 1,000..300,000 ms, polling 100..5,000 ms. A wait timeout
does not cancel the vendor task.

Only release resources explicitly returned as `runtime-owned`, using their returned
release fields. Keep user-owned and reused GUI sessions open. After upgrading,
`eda_connection_reset` refreshes the Runtime transport without closing EDA.

Do not place private project paths, manuals, credentials or task geometry in public
configuration, Skills or experience assets.
