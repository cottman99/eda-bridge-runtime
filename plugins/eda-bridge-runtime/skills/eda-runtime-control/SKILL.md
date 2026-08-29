---
name: eda-runtime-control
description: Use captured EDA context and the stable EDA Bridge Runtime path for ADS, AnsysEM, and other registered EDA bridges; applies to inspection, edits, simulations, durable jobs, and local or SSH execution.
---

# EDA Runtime Control

Use the Runtime MCP tools as the normal execution path. Local and SSH targets follow the
same workflow; transport selection comes from the connection registry, not from shell command
assembly in the conversation.

This Skill and its MCP server run on the Agent host. A separate EDA host runs
the selected vendor adapter service and EDA bridge. If both roles share one
machine, keep the same workflow and select a local connection; do not bypass
Runtime merely because SSH is absent.

## Route quickly

- Treat a copied `EDA_CONTEXT` as a bounded execution snapshot, not merely an opaque locator. When
  it and the selected vendor Skill establish one typed operation, call `eda.submit` directly; the
  Runtime resolves the origin and the adapter validates freshness inside that request.
- Use `eda.context.resolve` with one concise `purpose` only to inspect a Context without executing, diagnose an invalid or
  ambiguous binding, or expose its bounded snapshot to the user.
- Without context, call `eda.connections.list` with one concise `purpose`. If exactly one connection matches the requested
  EDA, use it. Ask one short question only when multiple connections remain genuinely ambiguous.
- Call `eda.capabilities` only when the operation is not established by the selected Skill or
  Context, its capability digest is stale, or a prior response reports an unsupported operation.
  Do not make it a routine preflight.
- If the user has no existing project, select the matching advertised `*.create` operation, create
  one isolated non-existing target, and continue with the returned `EDA_CONTEXT`. Do not search for
  a reference project or ask the user to maintain routing metadata merely to start from scratch.
- State a concise concrete `purpose` on every Runtime call. Add `expected_effect` when changing a
  design. Runtime records the agent/client metadata automatically.

## Execute safely

- Prefer a typed adapter operation. Inspect capabilities once only when support is uncertain; do not
  repeat doctor, environment, or full-state probes when the connection and target are unchanged.
- After capabilities establish a non-mutating operation, use `eda.read` so the Agent client can
  authorize the call through a statically read-only tool. Runtime rejects unknown or mutating
  operations on that lane. Keep `eda.submit` for mutations and unresolved safety classes. When the
  response contract is already known and the task needs only a few facts from a large result, add
  `result_view` selectors using RFC 6901 JSON Pointers relative to the Bridge result. Use only
  deterministic `value`, `count`, or `exists` modes; omit the view when exploration needs the full
  response. The same view is available on a terminal `eda.job.wait` and on read-only plan steps.
  Runtime rejects plan views on mutations before execution. Never guess a pointer.
- When 2..16 typed operations are already decided, ordered, and share one connection, use one
  `eda.run_plan` call instead of spending an Agent turn per step. Give every step its own concise
  `purpose`; give every mutating step its own stable `idempotency_key`; request `wait` only where a
  later step depends on a durable result. Runtime validates the whole plan before its first
  mutation, then stops at the first failed or non-terminal unawaited step. Do not use a plan for a
  single operation, open-ended diagnosis, branching engineering judgment, or unrelated targets.
- For a mutation, use one stable `idempotency_key` for the same intended change. A retry observes
  the same operation instead of starting a duplicate.
- An accepted durable job is not a completed job. Prefer one `eda.job.wait` call when the task can
  wait for completion. Use `eda.job.status` for one observation after reconnecting and incremental
  `eda.job.events` only for diagnostic detail; never resubmit merely because SSH or the conversation
  disconnected.
- Read the compact `run` projection for both synchronous and durable work. Its
  state is the EDA operation state; the outer status of a status-query call is
  only the success of that observation.
- Keep small corrections in the same candidate workspace. Create a frozen revision only at an
  explicit promotion or delivery gate.
- Use a verified native API or bounded script only when the adapter advertises that lane. Treat GUI
  automation as a bounded fallback and record why the typed path was unavailable.
- After a Bridge or Runtime upgrade, use `eda.connection.reset` once to close only the
  Runtime-owned transport. The next explicit operation starts a fresh local or SSH Bridge process;
  the EDA application is not closed or modified.

Do not place credentials, customer paths, raw shell commands, or task-specific geometry into the
public Runtime configuration, plugin, or Skill.
