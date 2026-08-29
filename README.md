# EDA Bridge Runtime

<img src="plugins/eda-bridge-runtime/assets/logo.png" width="180" alt="EDA Bridge Runtime logo">

`eda-bridge-runtime` is an agent-neutral execution layer for EDA automation.
It gives local and SSH-driven bridges the same request envelope, durable job
semantics, context handoff, timing evidence, and append-only execution ledger.

The runtime is intentionally not an EDA bridge and not an AI harness. Vendor
bridges keep their native API knowledge. Agents state a short purpose; the
runtime records what was requested, what actually ran, how long each phase
took, and what result or artifact was produced.

## Design promises

- Local and SSH execution use one protocol and one evidence model.
- Every agent-originated operation carries a concise `purpose`.
- Actor metadata is collected automatically where possible and records its
  provenance; missing metadata never blocks engineering work.
- Mutating requests are idempotent and auditable.
- Disconnection does not imply that a long EDA job failed.
- Context tokens contain locators and fingerprints, never credentials.
- EDA-specific behavior lives in adapters, not in the runtime core.

## Current alpha

`0.1.0a5` adds agent-host lifecycle auditing without changing tool permissions. Codex hooks record
session, turn, model, permission mode, tool-call identity, concise purpose, and a content hash before
an EDA Runtime call, then link the completed call to its actual Run. The audit is append-only,
hash-chained, and stores neither raw operation payloads nor chat transcripts.

`0.1.0a4` adds rich bounded Context snapshots, stable origin routing, direct
one-submit execution, and automatic origin binding during connection setup.
Vendor Skills can declare the Runtime MCP directly, so users select one
task-facing Skill rather than manually composing infrastructure Skills.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\eda-runtime doctor
```

See [Architecture](docs/ARCHITECTURE.md) and the
[protocol schema](docs/schemas/request-v1.schema.json). Host placement is
defined by the [agent-client, eda-worker, and combined deployment roles](docs/DEPLOYMENT_ROLES.md).

The proposed lightweight Pi Agent pilot is described in
[Pi Agent pilot](docs/PI_AGENT_PILOT.md). It reuses the same Runtime boundary instead of adding a
second SSH or EDA-control path.

The repository also includes a minimal [MCP and Codex plugin](docs/MCP_AND_CODEX.md). It resolves
named local/SSH connections without asking the agent to assemble transport commands on each call.
Sanitized real-host evidence is recorded in [acceptance results](docs/ACCEPTANCE.md).
