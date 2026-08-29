# Version 0.1 scope

## 0.1.0a7 — thin Agent adapters without another execution stack

- Add a native Pi package that maps exactly seven Pi tools to the seven Runtime MCP tools through
  one persistent child process.
- Accept bounded Agent-declared provider/model/reasoning/session/tool-call metadata while keeping
  MCP client identity independently observed.
- Keep Pi free of SSH routing, EDA API knowledge, retries, job state, and a second audit database.
- Provide a Runtime-only Pi profile that disables built-in tools and automatic global Skill
  discovery, then explicitly loads only Runtime, ADS, and AnsysEM operation Skills.

## 0.1.0a6 — agent-neutral facts and transport lifecycle

- Record MCP client identity, concise purpose, input fingerprint, timing, and Run linkage inside
  Runtime itself; Agent hooks are optional metadata enrichment rather than the primary fact path.
- Add one bounded connection reset that closes only the Runtime-owned transport and leaves EDA
  state untouched.
- Require a concise purpose for connection listing and Context resolution as well as execution.

## 0.1.0a5 — agent lifecycle audit

- Capture Codex lifecycle identity outside model context with plugin-scoped hooks.
- Keep tool permissions and inputs unchanged; never auto-approve an EDA operation for telemetry.
- Link the completed MCP call to its actual Runtime Run in an append-only hash chain.
- Record field provenance and omit raw operation payloads and chat transcripts.

## 0.1.0a1 — contracts and core

- Versioned request, response, event, identity, and context contracts.
- Append-only SQLite ledger with per-run hash chains.
- Local and SSH JSON-lines transports with handshake.
- Durable jobs, leases/fencing, adapter SDK, artifact manifests.

## 0.1.0a2 — bridge integration

- ADS interactive-session adapter and context integration.
- AnsysEM durable-job adapter and lightweight context add-in.
- Real local and remote sanitized acceptance tests.

## 0.1.0a3 — agent entry points

- Minimal MCP server and Codex plugin/Skill.
- Conformance, disconnect, resume, redaction, and timing evidence.
- Public documentation and stable alpha installation path.

## 0.1.0a4 — direct context execution

- Rich bounded Context snapshots with stable origin and live-session identity.
- Direct `eda.submit` fast path without mandatory resolve or capability preflight.
- Automatic origin probing during connection registration and v1 compatibility.
- Vendor Skill MCP dependency contract for one-Skill user interaction.
