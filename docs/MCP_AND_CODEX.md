# MCP and Codex plugin

The bundled plugin is a thin discovery layer. It starts `eda-runtime mcp serve`, while the Runtime
keeps transport, idempotency, durable jobs, and the execution ledger independent of Codex.
The plugin and Skill belong on the Agent host. A remote EDA host needs only the
shared Runtime protocol plus its vendor bridge and adapter service unless an
Agent also runs there.

The plugin also installs `PreToolUse` and `PostToolUse` hooks scoped only to its own MCP tools.
They write an Agent-host append-only audit that records the Codex session, turn, active model,
permission mode, tool-call identity, concise purpose, and a hash of the arguments. Completion links
that identity to the returned Runtime Run. Hooks do not rewrite inputs, approve tools, parse the
chat transcript, or store raw operation payloads. Inspect the bounded recent view with
`eda-runtime audit list`.

Codex asks for one-time trust when a new or changed plugin Hook is first used. Review and approve
the two bundled audit commands; routine calls need no extra Agent prompt after that. Automated
acceptance may use Codex's explicit hook-trust bypass only after validating the installed Hook file.

The stdio server supports both the legacy MCP initialization era through `2025-11-25` and the
stateless `2026-07-28` discovery era. It exposes six tools:

- `eda.context.resolve`
- `eda.connections.list`
- `eda.capabilities`
- `eda.submit`
- `eda.job.status`
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

The tools never accept a raw local or SSH launch command. They select a previously registered
connection by `connection_id`, by a stable `origin_id` in `EDA_CONTEXT`, or by an unambiguous EDA
match. Each Agent host may map the same origin to a different local or SSH route.

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
