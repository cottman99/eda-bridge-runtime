# Sanitized acceptance evidence

Acceptance used a remote Linux EDA host over one persistent SSH transport. No customer project,
credentials, host address, or task-specific geometry is included here.

## 2026-08-29 scoped unattended mutation evaluation

- The ordinary Codex profile rejected `eda.submit` under non-interactive
  `approval_policy=never`, proving the write gate remained active.
- A separate evaluation profile pre-approved only `eda.submit`; shell, GUI,
  browser, general plugins, and unrelated tools stayed disabled. It did not use
  global approval or sandbox bypass.
- The ADS L3 case created one disposable workspace and replayed the exact
  idempotency key in three calls. Scoring independently observed one explicit
  deduplication and one reused projected Run.
- The AnsysEM L3 case created one disposable project, waited for its durable
  Job, and replayed the exact key in four calls. Scoring independently observed
  one reused projected Run and one Job; no second project creation occurred.
- Both cases prohibited simulation and customer data. All named `/tmp`
  workspaces and project Bundles were removed after verification.
- Analysis of 134 existing Runtime calls separated 8 intentional idempotent
  replays from 23 potentially redundant discovery calls and 17 avoidable status
  polls. The report contained aggregate timings and finding counts only; no raw
  payload, customer path, Context token, connection identifier, or Run/Job id
  was emitted.

## 2026-08-29 Runtime alpha.9 safe-read and evaluation acceptance

- The Python suite passed 71 tests, Ruff and formatting checks; the Pi adapter passed all three
  Node tests against the candidate Runtime and exposed exactly nine MCP tools.
- Codex completed the ADS L2 case with exactly two successful calls: capability discovery followed
  by `eda.read`. It reported 13 live sessions without shell, GUI, mutation, retry, or permission
  rejection.
- Codex completed the AnsysEM L2 case with exactly three successful calls: capability discovery,
  `eda.read`, and one durable `eda.job.wait`. Fresh inspection confirmed a sanitized scratch Bundle
  and `edb.def`; no solve or customer project was used.
- The same scorer classified Pi startup as `agent_auth_unavailable` in 656 ms with zero tool calls,
  instead of misreporting it as a Runtime, SSH, or EDA failure.
- Real ADS and AnsysEM SSH capability calls completed in about 0.9 seconds; bounded close completed
  in 39-53 ms and left no new SSH descendant processes.

## 2026-08-29 Pi autonomous Runtime alpha.8 acceptance

- Pi `0.84.4` with `openai-codex/gpt-5.5` received one complete task file, read the selected
  vendor Skill, discovered capabilities once, and completed a fresh HFSS 3D Layout scratch-project
  create plus bundle inspection without shell, GUI, solve, or human correction.
- Repeating the identical mutation returned the same durable Run and job.
- Capability-aware submission classified the later project inspection as read-only without asking
  the model to inject Runtime bookkeeping into the vendor payload.
- `eda.job.wait` reduced the successful workflow from 28 tool calls and 29 assistant turns in the
  diagnostic run to 7 tool calls and 8 turns. Processed tokens fell from 374394 to 59350, elapsed
  time from 158 to 73 seconds, and reported model cost from USD 0.551460 to USD 0.137743.
- Independent fresh inspection confirmed the project file, EDB directory, and `edb.def`; no solve
  was run.

## 2026-08-29 Pi adapter and actor-metadata acceptance

- The Python suite passed 58 tests, including bounded Agent-declared actor metadata whose
  provenance remains distinct from observed MCP client identity.
- The Pi package client exposed exactly seven Runtime tools and completed a registry read.
- A real Pi 0.73.1 RPC session reported exactly seven `eda_*` tools and loaded only Runtime, ADS,
  and AnsysEM operation Skills after the launcher disabled automatic global Skill discovery.
- `/eda-runtime-status refresh` found two registered connections without opening EDA or SSH. Cold
  startup took 1013.4 ms; the second call through the same persistent process took 12.8 ms.
- A clean `0.1.0a7` wheel in an isolated Python environment was then called through the real Pi
  extension. Runtime recorded Pi family/version, reasoning, session, Skill, permission mode, and
  tool-call identity as declared facts; MCP client name/version and harness were independently
  observed. The hash-linked request/completion pair retained the concise purpose and completed in
  370 ms including cold process startup.

## 2026-08-29 agent-neutral audit and transport-reset acceptance

- A clean wheel installation of `0.1.0a6` exposed seven Runtime tools. The added
  `eda.connection.reset` closed one Runtime-owned ADS SSH child in 13 ms and returned
  `next_call=fresh_transport`; the next capability call opened a new process and passed. No EDA
  application was opened, closed, or modified.
- Fresh SSH capability reads passed for ADS and AnsysEM in 947 ms and 903 ms. ADS passed again in
  862 ms after the bounded reset. Earlier warm-process measurements were 125 ms for ADS and 16 ms
  for AnsysEM, confirming that normal calls retain persistent-transport latency benefits.
- Runtime wrote ten requested/completed audit events directly from the MCP server without a Codex
  Hook. The hash-chained records retained all five concise purposes, observed client identity,
  per-call timing, and three linked Runs while storing only an argument fingerprint.
- Acceptance first detected both remote Bridge environments on Runtime `0.1.0a4` even though the
  installed Bridge packages required `>=0.1.0a5`. Aligning only that dependency fixed protocol
  parsing; the reset acceptance covers loading an upgraded environment without restarting EDA.
- The repository passed 57 tests, Ruff checks, format checks, and wheel installation from a clean
  environment.

## 2026-08-29 Codex lifecycle-audit acceptance

- A freshly installed `0.1.0-alpha.5` plugin loaded its bundled
  `hooks/hooks.json` in a new Codex CLI session and called `eda.connections.list` exactly once.
  This non-interactive acceptance used Codex's explicit hook-trust bypass after the installed Hook
  file was inspected; normal interactive use presents the standard one-time trust review.
- The pre- and post-tool hooks produced two consecutive, hash-linked audit events. They observed
  the Codex model, session, turn, tool-call identity, permission mode, and concise declared purpose.
- The events stored a SHA-256 fingerprint instead of the raw MCP arguments. No chat transcript,
  customer data, connection details, or credentials were copied into the Agent audit.
- The diagnostic connection-list call correctly recorded `execution.linked=false` because it does
  not create an EDA Run. Runtime operation tests cover completion linkage to the returned Run view.
- The two hook records were 609 ms apart, including the MCP call itself. Hook handlers do not
  rewrite the pending call or return an allow decision, so telemetry cannot bypass tool approval.

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

## 2026-08-28 Context v2 and dual-role acceptance

- Both vendor Bridges emitted bounded `EDA_CONTEXT:v2` tokens containing a stable origin, session
  state, target summary, capability digest, and freshness state. Runtime selected the correct
  registered connection from the origin without a connection hint; legacy v1 decoding remains
  covered by tests.
- One ADS documentation query completed with a single `eda.submit` over the SSH route in 529 ms.
  One AnsysEM documentation query completed over the production SSH route in 860 ms. Neither path
  launched the EDA or required separate context-resolution and capability calls.
- The same Runtime and AnsysEM adapter completed a documentation-status request through a local
  connection in 72 ms when the EDA worker also acted as the Agent host. Only the connection record
  differed between the local and SSH paths.
- Acceptance caught that an SSH child initially inherited the host's default virtual display even
  though the captured Context named another display. The production connection commands now bind
  the display before launching either Bridge; the ledgers then observed the required display for
  both adapters.
- Connection setup probed each Bridge once and persisted its origin. Subsequent Context-driven
  requests did not spend an extra round trip rediscovering the target.

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
