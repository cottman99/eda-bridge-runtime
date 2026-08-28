# Sanitized acceptance evidence

Acceptance used a remote Linux EDA host over one persistent SSH transport. No customer project,
credentials, host address, or task-specific geometry is included here.

## ADS interactive path

- ADS 2026 Update 2.1 started an owned scratch workspace on virtual display 4.
- MCP stateless discovery returned protocol `2026-07-28` and five typed tools.
- Three read-only calls (`ping`, `status`, `ping`) passed through the same persistent SSH process.
- First-call wall time was 499 ms, including process and SSH startup. Reused-call wall times were
  45 ms and 36 ms; the final native bridge round trip was 15 ms.
- The append-only ledger retained the purpose, adapter version, capability decision, and native
  bridge timing for each call.

## AnsysEM durable path

- AEDT 2026.1 and PyAEDT 1.4.0 accepted a detached read-only job on virtual display 4.
- Submission returned an accepted receipt in 443 ms. The job reached `passed`; two later status
  polls took 15 ms and 16 ms without replaying the operation.
- Ledger evidence retained the declared purpose, selected runtime profile, observed display,
  adapter version, and terminal result.

## Package and failure-path checks

- Unit tests cover hash-chain integrity, source identity, handshake mismatch, malformed-frame
  isolation, idempotency, leases, durable jobs, orphan detection, connection ambiguity, legacy and
  stateless MCP discovery, context routing, and no-replay connection failure.
- Ruff lint and formatting checks pass.
- The Codex plugin manifest and bundled Skill pass their validators.
