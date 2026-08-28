# Sanitized acceptance evidence

Acceptance used a remote Linux EDA host over one persistent SSH transport. No customer project,
credentials, host address, or task-specific geometry is included here.

## 2026-08-28 convergence acceptance

- The installed Agent-side MCP exposed six typed tools, including `eda.capabilities`.
- Capability discovery through the registered SSH connections took 438 ms for ADS and 422 ms for
  AnsysEM on the first measurement. Both adapters reported `execution_host_role=eda-worker`; ADS
  reported a synchronous Run model and AnsysEM a durable Run model.
- ADS 2026 Update 2.1 created one disposable empty workspace on virtual display 4 in 1.55 seconds.
  A repeated call with the same idempotency key returned the original Run in 265 ms and did not
  recreate the workspace.
- AEDT 2026.1 / PyAEDT 1.4.0 created, saved, closed, and fresh-reopened one disposable empty HFSS
  3D Layout project on virtual display 4. Submission returned in 453 ms and the durable Run reached
  `passed` after 42.4 seconds. Status observations normally took 0--16 ms over the reused transport.
- Repeating the AnsysEM submission returned the same `job_id` and original `run_id`; later status
  and event calls observed that Run without replaying it.
- The first AnsysEM attempt exposed a missing propagation of the connection-level runtime profile
  into detached workers. The Bridge now inherits this profile automatically; a regression test and
  the successful real-host rerun cover the failure path.

## Evidence boundary

- Both append-only ledgers verified their hash chains after the real operations.
- Recorded facts include the concise declared purpose, MCP client and harness identity, observed
  host/display/runtime facts, adapter events, and terminal result. Metadata unavailable from the
  client remains explicitly `unknown` with provenance instead of being guessed.
- Scratch output completeness was checked, then the disposable artifacts were removed. No customer
  model was opened, no solve was launched, and no GUI automation was used.

## Package and failure-path checks

- Unit tests cover hash-chain integrity, source identity, handshake mismatch, malformed-frame
  isolation, idempotency, leases, durable jobs, orphan detection, connection ambiguity, legacy and
  stateless MCP discovery, context routing, and no-replay connection failure.
- Runtime, ADS adapter, and AnsysEM adapter tests pass; lint passes for Runtime, AnsysEM, and all
  modified ADS files. The wider ADS repository retains unrelated pre-existing lint debt.
- The Codex plugin manifest and bundled Skill pass their validators.
