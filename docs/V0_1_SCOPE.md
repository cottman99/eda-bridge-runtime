# Version 0.1 scope

## 0.1.0a11 — clean Agent context and evidence-safe comparisons

- Ignore hidden Skill backup and archive directories when generating a narrow
  Codex profile, preventing historical copies from re-entering the prompt.
- Apply the declared reasoning budget to both Codex and Pi evaluation clients
  and retain it in normalized results.
- Attribute repeated discovery, failure, and polling waste only within a
  stable observed or declared Agent session; never infer one shared session
  from repeated actions or an `unknown` identity.
- Preserve global idempotent replay counts when reuse of the exact Runtime Run
  supplies direct evidence across sessions.

## 0.1.0a10 — scoped unattended evaluation and audit analysis

- Generate a separate Codex evaluation profile that pre-approves only typed
  `eda.submit` calls after an operator has authorized unattended work; do not
  disable the sandbox or approve shell, GUI, browser, or unrelated MCP tools.
- Extend deterministic scoring with non-sensitive Run, Job, explicit
  deduplication, and repeated-Run facts so synchronous and durable Bridges can
  prove idempotent replay without trusting the Agent's final summary.
- Add disposable ADS and AnsysEM L3 cases covering create, terminal readback,
  and exact-key replay without simulation or customer data.
- Derive an action fingerprint that excludes the human-readable purpose and add
  an audit analysis view for redundant discovery, repeated failure, avoidable
  polling, idempotent replay, and conservatively estimated avoidable MCP time.

## 0.1.0a9 — safe read lane, bounded lifecycle, and reproducible Agent evaluation

- Close local and SSH JSON-lines workers through EOF first, then terminate only the isolated
  process tree within a fixed bound so cancelled MCP work does not leave child processes behind.
- Generate an optional narrow Codex EDA profile through native Codex profile and per-Skill
  enablement settings; keep the ordinary Codex configuration unchanged.
- Add deterministic public evaluation cases and a normalized scorer for Codex and Pi. Keep this
  developer evaluation harness outside the Runtime kernel and never commit real-host raw traces.
- Expose a statically read-only `eda.read` MCP tool that admits only operations proven non-mutating
  by cached Bridge capabilities; keep unknown and mutating work on `eda.submit`.
- Prefer an exact registered connection id over a redundant Agent-guessed EDA label while keeping
  captured Context identity strict.

## 0.1.0a8 — capability-aware submission and low-token durable waiting

- Cache advertised operation mutability per Runtime connection so read-only operations do not
  require the Agent to inject Runtime bookkeeping into vendor payloads.
- Add `eda.job.wait` so durable work can reach terminal state without one model turn per poll.
- Keep bounded structured Runtime facts visible to Pi while preserving full UI/audit details.

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
