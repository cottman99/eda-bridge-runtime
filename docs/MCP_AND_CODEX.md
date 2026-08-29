# MCP and Codex plugin

The bundled plugin is a thin discovery layer. It starts `eda-runtime mcp serve`, while the Runtime
keeps transport, idempotency, durable jobs, and the execution ledger independent of Codex.
The plugin and Skill belong on the Agent host. A remote EDA host needs only the
shared Runtime protocol plus its vendor bridge and adapter service unless an
Agent also runs there.

The MCP Runtime itself writes the Agent-host append-only audit for every supported client. It
records observed MCP client identity, concise purpose, a hash of the arguments, timings, and the
returned Runtime Run. This is the stable cross-Agent fact path.

An Agent adapter can attach `io.eda-runtime/actor` metadata to a tool call. Runtime accepts only a
bounded allowlist (agent family/version, provider, model, reasoning, Skill, session/turn/tool-call
identity, and permission mode) and labels it `declared`. MCP client name/version are taken from the
MCP handshake or call metadata and remain `observed`, so an adapter cannot overwrite that fact.

When a client does not declare an Agent session, Runtime assigns one random, non-identifying
correlation ID for that MCP server lifecycle and labels it `inferred`. This costs no Agent turn or
token, does not claim to know the chat-session identity, and still lets audit analysis compare calls
that demonstrably came through the same client connection.

The plugin additionally installs `PreToolUse` and `PostToolUse` hooks scoped only to its own MCP
tools. Where the Codex surface supports them, they enrich the same audit database with session,
turn, active model, permission mode, and tool-call identity. Hooks are optional: they do not define
whether the base Runtime record exists. Neither path parses the chat transcript or stores raw
operation payloads. Inspect the bounded recent view with `eda-runtime audit list`; it returns one
compact Runtime-observed row per executed call by default and does not double-count matching Hook
observations. Use `--full` only for explicit forensic inspection of the complete hash-chained events,
including Hook-only attempts and identity enrichment.
Use `eda-runtime audit analyze` for a privacy-preserving efficiency summary. It
separates intentional idempotent replay from repeated discovery, repeated
failure, and avoidable status polling, and reports bounded timing totals without
returning raw arguments, Context tokens, paths, or execution identifiers.
Per-tool totals and medians split Bridge/transport time from measured Runtime-local processing only
for paired timing samples. Calls from older or incomplete records without a transport measurement
remain explicitly `unpaired`; they are never subtracted from a different sample population.
Failed-call counts remain separate so a fast rejection is not mistaken for healthy performance.
The limit is measured in complete recent calls rather than raw event rows. Runtime
observations are authoritative when present, so enabling an Agent Hook does not
double-count the same MCP invocation; Hook-only observations remain a fallback.
Waste attribution is limited to repetitions inside one declared Agent session or one inferred MCP
client lifecycle. Global idempotent replay remains measurable because a reused Runtime Run proves
it, but calls in separate lifecycles are never guessed to be redundant.

Codex asks for one-time trust when a new or changed plugin Hook is first used. Review and approve
the two bundled audit commands; routine calls need no extra Agent prompt after that. Automated
acceptance may use Codex's explicit hook-trust bypass only after validating the installed Hook file.

The stdio server supports both the legacy MCP initialization era through `2025-11-25` and the
stateless `2026-07-28` discovery era. It exposes ten tools:

- `eda.context.resolve`
- `eda.connections.list`
- `eda.connection.reset`
- `eda.capabilities`
- `eda.read`
- `eda.submit`
- `eda.run_plan`
- `eda.job.status`
- `eda.job.wait`
- `eda.job.events`

Operation, status, and event calls include an additive compact `run` object.
It projects synchronous responses and durable jobs into one observation shape
and lists content-addressed evidence metadata without exposing artifact paths.

For a greenfield task, use the create operation established by the selected vendor Skill; discover
capabilities only when that operation is not known. ADS and AnsysEM intentionally keep different
creation schemas; both return a bounded, reusable `EDA_CONTEXT` without exposing credentials or
large private artifacts.

When a selected Skill and Context establish the operation, call `eda.submit` directly. Separate
`eda.context.resolve` and `eda.capabilities` calls are diagnostic and discovery tools, not mandatory
preflight. The adapter still validates the Context generation and target before execution.

Call `eda.read` directly for an intended non-mutating vendor operation. When its safety metadata is
not already in the current Runtime process, Runtime obtains capabilities mechanically through the
same connection, verifies the operation, and only then executes it. The Agent still sees one
statically read-only tool call and one logical audit action. Unknown or mutating operations are
rejected before vendor execution. Use explicit `eda.capabilities` for genuine exploration or schema
inspection, not routine permission plumbing.

A single `eda.read` or `eda.submit` can include a bounded `wait` policy. If the Bridge returns a
durable job, Runtime polls that existing job internally and returns its terminal response in the
same Agent call; it never resubmits the operation. Use `eda.job.wait` only when resuming a job that
was already returned, and `eda.job.status` for one observation after reconnecting.

For a known read response that is much larger than the facts needed by the task, `eda.read` accepts
an optional `result_view`. Each selector uses an RFC 6901 JSON Pointer relative to the Bridge
`result` and a deterministic `value`, `count`, or `exists` mode. Runtime receives the complete
Bridge response and creates the normal compact Run view before returning only the selected result
facts to the Agent. Invalid value/count pointers fail explicitly. Omitting `result_view` preserves
the full response, which remains the correct choice for exploration.
The same selector contract applies to a terminal `eda.job.wait` response and to read-only
`eda.run_plan` steps. A plan rejects `result_view` on a mutating step during prevalidation, before
any change begins.

For 2..16 already-decided operations on one connection, `eda.run_plan` performs one capability
preflight, validates the complete typed sequence before the first mutation, executes in order,
waits for explicitly marked durable dependencies, and stops on the first failure. Each step keeps
its own purpose and mutation idempotency key in the Runtime/Bridge facts. It is an execution
primitive, not an Agent planner: diagnosis, branching decisions, and cross-target orchestration
remain outside it.

The tools never accept a raw local or SSH launch command. They select a previously registered
connection by `connection_id`, by a stable `origin_id` in `EDA_CONTEXT`, or by an unambiguous EDA
match. Each Agent host may map the same origin to a different local or SSH route.

After an administrator upgrades a Bridge or its Runtime dependency, call `eda.connection.reset`
once for that registered connection. It closes only the Runtime-owned stdio/SSH process; the next
explicit tool call loads the upgraded environment while the engineer's EDA process remains open.

## One-time connection registration

Installation or administration code registers the connection once. Engineers normally copy
context from the EDA UI and do not maintain this file themselves.

```console
eda-runtime connection set --eda ansys-electronics-desktop --kind ssh \
  --host eda-host --ssh-option=-o --ssh-option=BatchMode=yes \
  ansys-lab /opt/eda/bin/ansysem-agent runtime serve

eda-runtime connection set --eda keysight-ads --kind local \
  ads-local ads-agent runtime serve
```

Registration probes the adapter once and stores its stable `origin_id`; engineers do not create or
maintain that identifier. `--origin-id` is an administrative override and `--no-origin-probe`
exists only for repair or legacy adapters.

The default registry is `~/.eda-bridge-runtime/connections.json`. Set `EDA_RUNTIME_HOME` to move
the whole Runtime control directory. Do not store credentials in the registry; SSH authentication
remains in the platform SSH configuration.

## Plugin source

The repository plugin lives at `plugins/eda-bridge-runtime`. Install the Python package first so
that `eda-runtime` is on the host path, then install the repository marketplace and plugin:

```console
codex plugin marketplace add cottman99/eda-bridge-runtime --ref main
codex plugin add eda-bridge-runtime@eda-bridge-runtime
```

Restart the Codex client after first installation so its Skill and MCP server are loaded together.
