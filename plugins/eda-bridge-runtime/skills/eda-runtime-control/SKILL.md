---
name: eda-runtime-control
description: Use captured EDA context and the stable EDA Bridge Runtime path for ADS, AnsysEM, and other registered EDA bridges; applies to inspection, edits, simulations, durable jobs, and local or SSH execution.
---

# EDA Runtime Control

Use the Runtime MCP tools as the normal execution path. Local and SSH targets follow the
same workflow; transport selection comes from the connection registry, not from shell command
assembly in the conversation.

## Route quickly

- If the user copied `EDA_CONTEXT`, call `eda.context.resolve` first. Use the resolved connection
  and do not rediscover the project, slot, design, display, or host in shell commands.
- Without context, call `eda.connections.list`. If exactly one connection matches the requested
  EDA, use it. Ask one short question only when multiple connections remain genuinely ambiguous.
- State a concise concrete `purpose` on every Runtime call. Add `expected_effect` when changing a
  design. Runtime records the agent/client metadata automatically.

## Execute safely

- Prefer a typed adapter operation. Inspect capabilities once when support is uncertain; do not
  repeat doctor, environment, or full-state probes when the connection and target are unchanged.
- For a mutation, use one stable `idempotency_key` for the same intended change. A retry observes
  the same operation instead of starting a duplicate.
- An accepted durable job is not a completed job. Use `eda.job.status` or incremental
  `eda.job.events`; never resubmit merely because SSH or the conversation disconnected.
- Keep small corrections in the same candidate workspace. Create a frozen revision only at an
  explicit promotion or delivery gate.
- Use a verified native API or bounded script only when the adapter advertises that lane. Treat GUI
  automation as a bounded fallback and record why the typed path was unavailable.

Do not place credentials, customer paths, raw shell commands, or task-specific geometry into the
public Runtime configuration, plugin, or Skill.
