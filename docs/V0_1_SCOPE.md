# Version 0.1 scope

## 0.1.0a32 — lossless UTF-8 motives on Windows

- Force UTF-8 at the MCP and Agent-hook protocol boundary instead of inheriting the Windows active
  code page. Natural-language purposes and Agent metadata therefore remain lossless in both
  execution and audit records.
- Cover MCP request identifiers and Codex Hook purposes under an explicit CP936 pipe simulation so
  future Windows releases cannot silently reintroduce mojibake.

## 0.1.0a31 — complete compact view of Runtime facts

- Keep bounded bypass facts visible beside normal MCP calls in the default compact audit query.
  The append-only ledger already retained these events; this corrects only the source-selection
  projection and does not change EDA execution.
- Declare the two included authoritative sources in the compact response while retaining the
  existing source-policy field for compatible consumers.

## 0.1.0a30 — owned interactive resources and complete local audit facts

- Standardize token-free audit views for Runtime-owned EDA resources while leaving exact release
  authority with each vendor Bridge.
- Materialize connection, EDA, operation, evidence count, resource state, and already-reported
  Bridge timing into the local Runtime ledger under the same call record.
- Infer stable Codex, Pi, and Claude agent-family facts from the observed MCP client without asking
  the Agent to assemble metadata or guessing unavailable model details.
- Provide a bounded bypass record for the exceptional operation that has no typed Runtime route;
  record motive, lane, and outcome without retaining raw commands or GUI input.

## 0.1.0a29 — one version-locked Codex execution path

- Use the configured Runtime command for both the MCP server and its Codex audit hooks, so a
  side-by-side or versioned installation cannot silently mix two Runtime releases.
- Quote a trusted Runtime executable path containing spaces and reject quotes or newlines in that
  generated command boundary.
- Add user-facing complete-workflow visuals and exact retained ADS/HFSS timing evidence without
  treating synthetic acceptance fixtures as customer or RF-valid designs.

## 0.1.0a28 — complete workflows without polling turns

- Allow an explicitly requested durable wait of up to five minutes while retaining the 60-second
  default and durable reconnect path. This lets one validated plan contain a small real HFSS solve
  without forcing another Agent turn solely because the former 90-second ceiling expired.
- Keep the Pi transport timeout slightly beyond Runtime's maximum bounded wait so the client never
  abandons a valid Runtime request first.
- Pass Pi evaluation prompts through its native `@file` input, avoiding Windows command-line length
  limits without adding a read tool, shell step, or retained raw prompt artifact.
- Add complete disposable ADS circuit-to-DDS and AnsysEM layout-to-report evaluation contracts.

## 0.1.0a27 — unambiguous execution timing

- Report canonical adapter/EDA-boundary and Runtime-local timing names while retaining the original
  field names as explicit compatibility aliases.
- State mechanically that packet-level network time is not measured, preventing local or SSH
  adapter wait from being misreported as pure network latency.

## 0.1.0a26 — source-free Pi profile installation

- Package the reviewed thin Pi Runtime extension and profile installer with the Python Runtime,
  removing the source-checkout dependency from a dedicated Pi Agent host.
- Expose the same `agent-profile <agent> install` CLI family for Codex and Pi without adding a new
  service, transport, job store, or audit path.
- Keep the existing Pi credential-preservation boundary, separate work/login/status launchers,
  read-only built-in tool set, and explicit vendor Skill selection.
- Retain one canonical copy of the Pi JavaScript adapter under `integrations/`; the wheel includes
  only its runtime package, extension, library, and Skill assets, not repository tests or docs.

## 0.1.0a25 — direct MCP transport retained in isolated Codex profiles

- Keep Codex's internal Code Mode host enabled because Codex 0.151 uses that process for direct MCP
  transport, while keeping Agent-visible Code Mode and shell tools disabled.
- Add a generated-profile regression assertion so future isolation changes cannot silently remove
  the only intended Runtime execution path.

## 0.1.0a24 — source-free Agent profile installation

- Package the Codex EDA profile generator in the Runtime CLI, so a local or remote Agent host can
  install or refresh its isolated execution path without cloning this repository.
- Keep the repository installer as a thin compatibility wrapper around the packaged implementation,
  preventing drift between development and installed-host behavior.
- Discover and disable inherited non-Runtime MCP servers and unrelated Skills only inside the EDA
  profile; preserve the user's ordinary Codex configuration unchanged.
- Count every non-passive Codex event as a tool attempt in evaluations and keep launch-failure
  classification separate from child-command output, closing two false zero-action result paths.
- Add underspecified ADS and AnsysEM guard cases that require zero execution attempts and one concise
  blocking question before any engineering mutation can begin.

## 0.1.0a23 — explicit plan structure and complete cross-Agent ladder

- Describe vendor payload and Runtime step controls as separate machine-visible fields in both MCP
  and Pi schemas, so durable `wait` policy cannot be mistaken for a vendor operation parameter.
- Require explicit bounded-solver approval independently from disposable-mutation approval in the
  evaluation runner and matrix.
- Retain authenticated Codex/Pi evidence for exact idempotent replay, complete ADS and AnsysEM
  lifecycles, one real generated-input Momentum solve, and one-turn cross-EDA coordination.
- Keep one plan and failure boundary per vendor during cross-EDA work; do not introduce a false
  cross-vendor transaction or rollback guarantee.

## 0.1.0a22 — precise Agent targeting and authenticated comparison

- Filter compact audit calls and aggregate timing by one exact Agent session, one linked Bridge
  Run, or both, while retaining complete request/completion pairs and bounded recent-call scans.
- Expose linked execution Run and job identities in compact rows without returning tool arguments.
- Interleave cross-Agent evaluations by case and trial while keeping every EDA action sequential,
  and record the actual execution order.
- Add a one-turn, two-connection read-only case that measures cross-EDA coordination without
  pretending to offer a cross-vendor transaction.
- Give `connection_id` and `eda` distinct machine-visible meanings so Agents do not put a
  registered connection name into the vendor-type selector.
- Generate separate login and native status launchers for isolated Pi EDA profiles, preserving
  credentials while preventing default-profile readiness from being mistaken for EDA-profile readiness.
- Retain the first authenticated Codex/Pi baselines from Runtime discovery through bounded
  vendor-document source selection, and classify an explicit zero-call client tool-unavailable
  result separately from Runtime, Bridge, EDA, and reasoning failures.

## 0.1.0a21 — correlated audit sessions and honest timing boundaries

- Keep generated Codex EDA profiles narrow by explicitly disabling built-in system Skills as well
  as unrelated installed and cached Skills; evaluation cases expose only their declared tools.
- Infer one anonymous correlation ID per MCP client lifecycle when an Agent cannot declare its own
  session, without spending another Agent turn or pretending to know the chat-session identity.
- Report paired Runtime/Bridge timing samples, missing measurements, failure counts, medians, and
  transport-boundary share without mislabeling Bridge/EDA wait time as pure SSH network latency.

## 0.1.0a20 — Agent-safe result projection and isolated evaluation

- Describe `result_view` as an advanced optimization that must be omitted until every pointer has
  been verified from an earlier full response for the same operation and version.
- Make evaluation runs expose only the Runtime tools declared by the selected case and require a
  typed JSON final response without forcing the expected values.
- Keep a failed no-tool Agent trial visible as an Agent reliability result rather than classifying
  it as Runtime, SSH, Bridge, or EDA failure.

## 0.1.0a19 — mechanical read safety preflight

- Let an intended typed `eda.read` directly trigger missing capability metadata discovery inside
  Runtime, preserving one Agent call and one logical audit action.
- Reject unknown or mutating operations after the mechanical preflight and before the vendor
  operation executes; never trust an Agent-declared mutability flag.
- Keep explicit capabilities for genuine exploration and schema inspection, not routine permission
  plumbing in every cold Agent session.

## 0.1.0a18 — one-call durable operations

- Let a single typed `eda.read` or `eda.submit` request include a bounded wait policy and return the
  terminal durable result without requiring a second Agent tool decision.
- Keep `eda.job.wait` for reconnecting to an already-returned job and `eda.job.status` for one
  post-reconnect observation; do not change Bridge job persistence or replay semantics.
- Preserve terminal result projection for waited reads, mutation idempotency, timeout visibility,
  and one logical Runtime audit call.

## 0.1.0a17 — durable and planned bounded reads

- Carry the same deterministic `result_view` through terminal `eda.job.wait` responses and
  read-only `eda.run_plan` steps so synchronous ADS and durable AnsysEM reads share one contract.
- Reject a plan result view on every mutating step during prevalidation, before the first change.
- Make the generated Pi launcher load the Runtime extension and administrator-selected EDA Skills
  itself while exposing read plus the ten Runtime tools and excluding shell/write/edit.

## 0.1.0a16 — deterministic bounded read results

- Add an optional `result_view` to the statically read-only lane so known large Bridge results can
  return exact selected values, counts, or existence facts without entering the Agent context in
  full.
- Use bounded RFC 6901 JSON Pointers only; reject missing value/count paths and preserve full
  responses as the default exploratory behavior.
- Measure the same real ADS session-status task before and after projection, retaining exact
  correctness and the normal Runtime Run evidence.
- Make `audit analyze` use the same complete-call, Runtime-preferred source policy as compact audit
  listing so Hook observations and interleaved event writes cannot distort efficiency findings.

## 0.1.0a15 — context-light audit retrieval and bounded Windows cleanup

- Keep full append-only audit events unchanged while making recent-call retrieval a compact,
  Runtime-observed projection; explicit `--full` remains available for forensic inspection.
- Query complete recent run groups from SQLite so concurrent event writes cannot split a call, and
  avoid double-counting optional Codex Hook observations as additional EDA executions.
- On forced Windows transport shutdown, snapshot descendants, detect a failed `taskkill`, terminate
  still-live captured processes directly, and wait within the existing bounded close budget.

## 0.1.0a14 — canonical Skill selection

- Keep historical plugin caches intact while enabling exactly one canonical path for each requested
  Skill name in generated Codex EDA profiles.
- Prefer an explicitly installed direct Skill; otherwise select the highest versioned plugin-cache
  copy and explicitly disable older copies.
- Retain deterministic regression coverage for both duplicate-cache and direct-install precedence.

## 0.1.0a13 — validated deterministic execution plans

- Execute 2..16 already-decided typed steps through one Agent call and one persistent connection;
  keep planning and engineering judgment in the Agent.
- Preflight every effective target and all mutation identities before the first change, then stop
  at the first failed, interrupted, or unawaited non-terminal step.
- Preserve per-step purpose, Run, Job, timing, and privacy-bounded audit evidence across Codex and
  Pi, including partial evidence when transport or durable waiting is interrupted.
- Add a one-call AnsysEM L5 evidence case and nested-run scoring for direct before/after measurement.

## 0.1.0a12 — bounded evidence and reproducible cross-Agent matrices

- Add ADS and AnsysEM L4 cases that find and expand one version-matched API
  source without launching EDA, mutating projects, or retaining document text.
- Retain aggregate response character counts in normalized results so the
  scorer can prove substantive responses and compare context pressure without
  exposing payloads.
- Run bounded Codex/Pi matrices sequentially, require explicit mutation
  approval, stop repeated work after an authentication failure, and keep
  provider-specific model selectors explicit.
- Install or refresh the dedicated Pi EDA profile while preserving unknown
  settings and proving any existing `auth.json` is unchanged; missing or empty
  credentials remain an explicit interactive-login boundary.

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
