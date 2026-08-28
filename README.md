# EDA Bridge Runtime

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

`0.1.0a3` adds the minimal Codex plugin and completes the registered persistent
local/SSH entry point. ADS and AnsysEM now use the same intent, identity,
timing, reconnect, and durable-job model.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\eda-runtime doctor
```

See [Architecture](docs/ARCHITECTURE.md) and the
[protocol schema](docs/schemas/request-v1.schema.json).

The repository also includes a minimal [MCP and Codex plugin](docs/MCP_AND_CODEX.md). It resolves
named local/SSH connections without asking the agent to assemble transport commands on each call.
Sanitized real-host evidence is recorded in [acceptance results](docs/ACCEPTANCE.md).
