# MCP and Codex plugin

The bundled plugin is a thin discovery layer. It starts `eda-runtime mcp serve`, while the Runtime
keeps transport, idempotency, durable jobs, and the execution ledger independent of Codex.

The stdio server supports both the legacy MCP initialization era through `2025-11-25` and the
stateless `2026-07-28` discovery era. It exposes five tools:

- `eda.context.resolve`
- `eda.connections.list`
- `eda.submit`
- `eda.job.status`
- `eda.job.events`

The tools never accept a raw local or SSH launch command. They select a previously registered
connection by `connection_id`, by a hint in `EDA_CONTEXT`, or by an unambiguous EDA match.

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
