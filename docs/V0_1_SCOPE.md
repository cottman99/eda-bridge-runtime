# Version 0.1 scope

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
