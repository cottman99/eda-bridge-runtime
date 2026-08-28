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

- If the user copied `EDA_CONTEXT`, call `eda.context.resolve` first. Use the resolved connection
  and do not rediscover the project, slot, design, display, or host in shell commands.
- Without context, call `eda.connections.list`. If exactly one connection matches the requested
  EDA, use it. Ask one short question only when multiple connections remain genuinely ambiguous.
- Before guessing an operation or researching a vendor API, call `eda.capabilities` once for the
  resolved target. Use the advertised operation schema and mutation classification.
- If the user has no existing project, select the matching advertised `*.create` operation, create
  one isolated non-existing target, and continue with the returned `EDA_CONTEXT`. Do not search for
  a reference project or ask the user to maintain routing metadata merely to start from scratch.
- State a concise concrete `purpose` on every Runtime call. Add `expected_effect` when changing a
  design. Runtime records the agent/client metadata automatically.

## Execute safely

- Prefer a typed adapter operation. Inspect capabilities once when support is uncertain; do not
  repeat doctor, environment, or full-state probes when the connection and target are unchanged.
- For a mutation, use one stable `idempotency_key` for the same intended change. A retry observes
  the same operation instead of starting a duplicate.
- An accepted durable job is not a completed job. Use `eda.job.status` or incremental
  `eda.job.events`; never resubmit merely because SSH or the conversation disconnected.
- Read the compact `run` projection for both synchronous and durable work. Its
  state is the EDA operation state; the outer status of a status-query call is
  only the success of that observation.
- Keep small corrections in the same candidate workspace. Create a frozen revision only at an
  explicit promotion or delivery gate.
- Use a verified native API or bounded script only when the adapter advertises that lane. Treat GUI
  automation as a bounded fallback and record why the typed path was unavailable.

Do not place credentials, customer paths, raw shell commands, or task-specific geometry into the
public Runtime configuration, plugin, or Skill.
