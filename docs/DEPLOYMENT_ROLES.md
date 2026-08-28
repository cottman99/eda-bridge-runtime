# Deployment roles

The Runtime uses two independent host roles. They may be installed on separate
machines or combined on one machine; the execution contract does not change.

## Agent client

The agent host owns the user-facing Skill, MCP server, connection registry,
context resolution, and transport reuse. It does not need the EDA application
or a vendor bridge installed locally when the selected connection is SSH.

Required components:

- `eda-runtime mcp serve` and the Runtime Codex plugin;
- `~/.eda-bridge-runtime/connections.json` or an explicitly selected registry;
- the thin Runtime routing Skill;
- platform SSH configuration when an EDA worker is remote.

## EDA worker

The EDA host owns the vendor adapter service, bridge, EDA add-on or add-in, EDA
process, durable worker state, and vendor evidence. It does not need Agent
Skills or the Runtime Codex plugin unless an Agent also runs on that host.

Required components:

- the shared Runtime protocol library;
- one vendor bridge and its Runtime adapter service;
- the intended EDA installation, runtime profile, display, and license;
- host-side job, ledger, and artifact state used by that bridge.

## Combined host

A combined host installs both roles and selects a `local` Runtime connection.
It still traverses MCP, Runtime, and the vendor adapter; only SSH is removed.
This preserves purpose, actor, idempotency, Run, and evidence behavior between
local and remote deployments.

```text
Agent host                                      EDA host
-----------                                     --------
Agent -> Skill -> MCP -> Runtime client         Runtime adapter service
                         |                      -> vendor bridge
                         +-- local or SSH ------> -> EDA add-on/API -> EDA
```

Skills are Agent instructions, not remote execution services. Documentation
query backends and licensed corpora may live on either host, but their
user-facing Skill belongs wherever the Agent runs.

## Installation-state proof

An Agent capability is usable only when four states agree:

1. repository source;
2. installed Python package;
3. installed plugin and Skill cache;
4. tools exposed to a freshly started Agent session.

An EDA worker is proven separately by its installed bridge version, adapter
capabilities, EDA/profile identity, and a bounded real-host acceptance check.
Static Skills found on an EDA-only host do not participate in a remote Agent's
route and must not be treated as worker dependencies.
