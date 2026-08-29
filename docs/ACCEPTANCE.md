# Sanitized acceptance evidence

Acceptance used a remote Linux EDA host over one persistent SSH transport. No customer project,
credentials, host address, or task-specific geometry is included here.

## 2026-08-30 task-scoped audit and balanced evaluation candidate

- The complete suite passed 137 tests with Ruff check and format check clean.
- A real recent AnsysEM capability call was selected by both its inferred MCP lifecycle session and
  linked Bridge Run. Analysis returned exactly one complete request/completion pair, one successful
  tool call, 1,016 ms measured transport, and no waste finding; unrelated audit history was absent.
- A two-trial Codex/Pi scheduling acceptance alternated the planned first client. Codex passed 2/2;
  Pi's missing interactive login was classified once in 468 ms and its later trial was skipped.
  The matrix did not label authentication as a Runtime, Bridge, SSH, or EDA failure.

## 2026-08-30 Runtime a21 repeated read-only baseline

- Fifteen independent Codex trials passed across Runtime discovery, ADS and AnsysEM capability
  discovery, one typed ADS session read, and one durable AnsysEM Bundle read. Every case used
  exactly one allowed Runtime call; no solve, GUI action, customer data, or raw Agent trace was
  retained.
- Each case had three trials with a 100% strict, semantic, and wall-budget pass rate. Median wall
  times were 17.219 s, 16.703 s, 17.656 s, 19.657 s, and 19.562 s respectively.
- Against the same Codex `gpt-5.5` low-reasoning a20 baseline, those medians improved by 4.615 s,
  9.706 s, 4.629 s, 6.382 s, and 6.963 s (about 21%, 37%, 21%, 25%, and 26%) without changing the
  correctness gates. The measured Bridge/SSH/EDA boundary remained about 0-12% of read-task wall
  time, so this evidence does not justify additional SSH command-layer complexity.
- The AnsysEM read fixture was created once through a disposable-only idempotency case, then all
  three owned remote Bundle artifacts were removed after the read trials. Fixture setup evidence is
  not mixed into the read-latency baseline.
- A separate three-trial cross-EDA case selected the exact ADS and AnsysEM connections in one Agent
  turn and passed both capability reads with exactly two Runtime calls every time. Its 19.687 s
  median was 14.672 s (42.7%) below the sum of the two independent capability-case medians, while
  median input fell from 71,024 combined tokens to 37,271. This supports batching already-known,
  independent EDA observations into one turn; it does not introduce or claim a cross-vendor
  transaction.
- The sanitized three-trial reference is checked in as
  `evals/baselines/codex-gpt55-low-runtime-a21-20260830.json`; transient per-trial files remain
  untracked.

## 2026-08-30 Runtime alpha.21 correlated-audit acceptance

- The complete Python suite passed 135 tests; Ruff check and format check passed across 56 files.
- A clean wheel and source distribution passed Twine validation. A fresh isolated environment
  installed the wheel without an index, reported `0.1.0a21`, and passed Runtime doctor.
- A fresh MCP process with an empty connection registry executed the same discovery twice without
  declared Agent metadata. Both calls received one stable anonymous inferred session, and audit
  analysis identified exactly one same-lifecycle redundant discovery without a Codex Hook.
- On 346 historical Runtime calls, the paired-timing analyzer retained 336 comparable samples and
  isolated 10 legacy calls with missing transport measurements. It did not subtract unmatched
  populations. Runtime-local measured processing was 157.253 ms across the paired calls; the
  transport boundary intentionally remains Bridge/EDA-inclusive and is not called pure SSH latency.
- The generated Codex EDA profile exposed five task-facing EDA Skills, explicitly disabled 210
  unrelated or older Skills including the built-in system catalog, and removed the client warning
  about shortened Skill descriptions. Three Runtime discovery trials passed 3/3 with 26.9% lower
  median wall time than the earlier profile baseline; ADS and AnsysEM results remain separately
  recorded below so the release does not claim a universal latency improvement.
- Trusted Publishing built, tested, published, and reinstalled the exact public `0.1.0a21` package.
  The public package was then installed in the local and remote shared Runtime plus both isolated
  vendor-Bridge environments; all six imports reported the same version. Remote doctor preserved
  the required virtual display.
- One final installed-profile Codex discovery used exactly one Runtime call and passed with two
  registered connections. The audit row included an automatically inferred MCP lifecycle ID. Its
  29.342-second wall time is retained as an installed-state correctness sample, not presented as a
  latency improvement over the repeated pre-release baseline.
- Installed-state vendor acceptance also passed on the one permitted remote display: ADS session
  status used one read; AnsysEM created one disposable project and replayed the same mutation key
  without a duplicate job; a fresh one-call inspect then confirmed the persisted Bundle. No solve
  ran, and all three temporary Ansys artifacts were removed after verification. Agent-side time
  remained the majority of both read cases, while the creation case correctly spent most of its
  measured time inside the Bridge/EDA boundary.

## 2026-08-29 Codex profile system-Skill isolation

- The dedicated EDA profile generator previously ignored every hidden directory, which correctly
  excluded user backups but also omitted Codex's official `.system` Skill root from its disable
  rules. The generator now recognizes only that named hidden root and continues to ignore nested or
  unrelated hidden backups.
- This follows the official `skills.config enabled=false` mechanism. Codex's official source marks
  disabled catalog entries non-model-visible before rendering; no parallel Skill loader or custom
  prompt layer was added. See [Codex Skills](https://developers.openai.com/codex/skills/) and the
  pinned [catalog visibility implementation](https://github.com/openai/codex/blob/6478a751fde8884b2fdc76486fe23175a8e795d4/codex-rs/ext/skills/src/catalog.rs).
- After regenerating the local profile, the Skill-description budget warning disappeared. Three
  repeated L0 connection reads passed 3/3; median wall time was 21.834 s versus the prior 29.855 s,
  and median input was 34,667 versus 36,393. The sample supports profile hygiene and the measured
  result, not a universal latency claim.
- Six same-contract AnsysEM L2 reads passed 5/6. Every passing run used one `eda.read`; the sole
  failure made no tool attempt and entered neither Runtime nor SSH. That remaining Codex selection
  limitation is preserved in the baseline rather than hidden by an evaluator retry or misassigned
  to the EDA stack.
- ADS remained stable after the same profile change: three `session.status` reads passed 3/3 with
  a 26.039-second median and 36,853 median input tokens. Three bounded `docs.query` → `docs.get`
  workflows also passed 3/3 using only the private ADS documentation lane. Their median input fell
  from the earlier single sample's 74,064 to 52,162; the 34.283-second median wall time was slower
  than that sample, so only context reduction and routing reliability are claimed.

## 2026-08-29 Runtime alpha.20 Agent-contract acceptance

- The Codex evaluator now exposes only each case's declared Runtime tools and generates a strict
  final-response shape from the case contract. It does not put expected values into the Schema;
  the deterministic scorer still decides correctness. This removed accidental `eda.run_plan`
  selection and prose-only JSON failures from the measurement boundary.
- With the prior Runtime tool description, all three isolated AnsysEM read trials guessed
  unverified `result_view` pointers and were correctly rejected after the EDA read. The revised
  public Schema states that projection is an advanced optimization whose pointers must come from
  an earlier successful full response, not from desired final-answer keys.
- Against the source candidate, two of three repeated AnsysEM inspections then passed in one
  `eda.read` each, with no guessed projection. Median wall time was 22.994 s, median input was
  37,488 tokens, and measured Runtime/SSH/Bridge transport was about 1.94--2.03 s in the passed
  trials. The remaining trial made no tool call and returned failed fields; it remains recorded as
  a Codex selection failure rather than being hidden or attributed to Runtime/AnsysEM.
- No execution semantics, mutation permissions, SSH routing, or vendor payloads changed. The
  candidate adds interface guidance plus evaluation isolation, and preserves full responses as
  the default exploratory behavior.
- All 133 Python tests, Ruff checks, formatting checks, three Pi adapter tests, wheel/sdist builds,
  Twine metadata checks, and the packaged private-identifier scan passed.
- The built wheel was installed into the local Runtime and the remote combined Runtime, ADS, and
  AnsysEM environments; all reported `0.1.0a20`. A final installed-profile AnsysEM read on
  `DISPLAY=:4.0` passed in one call with a 2.063-second measured transport, after which the exact
  disposable Bundle and uploaded wheel were verified removed.

## 2026-08-29 Runtime alpha.19 mechanical read-preflight acceptance

- Three real ADS session-status trials each used exactly one `eda.read`. Runtime mechanically
  obtained the missing capability metadata, verified the read-only boundary, executed the typed
  read, and returned only the exact projected count. All three passed. Agent calls fell from two to
  one, median input tokens from 52,781 to 37,859 (28.3%), and model-visible response characters
  from 2,731 to 20. Median wall time fell from 26.382 to 25.791 s while Runtime/SSH/ADS remained
  about 1.17 s; the release does not generalize that small latency difference.
- A real AnsysEM fresh project inspect likewise used exactly one inline-wait `eda.read`. Calls fell
  from the original three-call lifecycle to one, input tokens from 66,853 to 51,634 (22.8%), and
  response characters from 2,840 to 954. Wall time was 31.236 s versus the prior 35.063-second
  median; each is a small sample, so the release claims call and context reduction, not latency.
- Unit coverage proves a mutating operation requested through the read lane triggers the same
  mechanical metadata preflight and is rejected before the vendor operation executes. Compact
  audit retained one logical read rather than attributing internal discovery to the Agent.
- The L4 documentation workflow retained the two genuine Agent decisions—bounded query and
  evidence selection—while removing the capability turn. ADS passed its two-read case. AnsysEM's
  prose-form payload contract passed 3/5 samples; expressing the same vendor payloads as exact JSON
  then passed 3/3 with a 29.563-second median. This was fixed in the evaluation contract rather
  than by adding a document-specific Runtime API.
- The complete 127-test Python suite, Ruff, formatting, package build, Twine checks, and all three
  Pi adapter tests passed. Local and remote Runtime/plugin installs plus both isolated remote Bridge
  environments report the alpha.19 candidate. The disposable AnsysEM Bundle and staging files were
  removed after exact-path verification.
- A clean PyPI dependency-resolution dry run for the public ADS alpha.36 and AnsysEM alpha.4
  packages selected Runtime alpha.19 automatically. Existing compatible installations are not
  forcibly upgraded, while new Bridge installations receive the current Runtime dependency.

## 2026-08-29 Runtime alpha.18 one-call durable-operation acceptance

- A real AnsysEM project inspect used one capability call plus one inline-wait read and returned the
  same fresh bundle facts as the prior three-call lifecycle. Agent tool calls fell from three to
  two, and input tokens fell from the prior three-trial median of 66,853 to 52,565 (21.4%). Wall
  time was 33.221 s; the single sample is not used as a latency claim.
- A separate disposable AnsysEM creation used one inline-wait mutation and one exact idempotent
  replay. It completed the same correctness contract in three Agent calls instead of four and used
  84,928 input tokens versus 101,851 in the prior direct baseline (16.6% less). AEDT execution was
  slower in this sample, so the 127.383-second wall time missed the unchanged 120-second SLO while
  remaining semantically correct; the budget was not relaxed after observation.
- Compact audit retained the inline wait as one logical `eda.read` or `eda.submit`; internal job
  polling did not appear as extra Agent behavior. Both disposable Bundles and all staging files
  were removed after exact-path verification.
- The complete 126-test Python suite, Ruff, formatting, package build, Twine checks, and all three
  Pi adapter tests passed. The candidate Runtime and plugin were installed on the local Agent host
  and the remote combined host; both isolated remote Bridge environments report `0.1.0a18`.

## 2026-08-29 Runtime alpha.17 durable and planned bounded-read acceptance

- One real ADS read plan obtained the exact 13-session count and `ok` Bridge status through two
  projected `session.status` steps. It used one Runtime connection, 1.328 s measured transport,
  and no mutation, GUI automation, or solve.
- The same two-step plan without views returned 15,408 structured characters; the projected plan
  returned 1,654, an 89.3% reduction. The unprojected facts were intentionally omitted from the
  measurement output rather than copied into logs or documentation.
- Regression tests apply the same view after a terminal durable wait, preserve full failures and
  non-terminal states, and reject every plan view on a mutating step before the first change.
- The self-contained daily Pi launcher loaded five selected Skills and exposed ten Runtime tools
  plus read. An authentication-free RPC status call found two configured EDA connections in
  181.4 ms; shell/write/edit were absent and the empty credential file remained unchanged.
- The complete 119-test Python suite, Ruff, formatting, and all three Pi adapter tests passed.

## 2026-08-29 bounded Codex model-routing probe

- With the same narrow profile and Runtime targets, the initial `gpt-5.6-luna` probe passed the ADS
  and AnsysEM L1 capability cases but changed the exact L0 contract from `status=ready` to
  `status=ok`; the deterministic scorer correctly rejected it.
- A subsequent matched three-trial L0 sample made the distinction conclusive for this bounded
  contract. `gpt-5.5` was semantically correct in 3/3 trials, passed the strict 30-second contract
  in 2/3, and had a 29.855-second median. Luna was semantically correct in 0/3: two trials reported
  zero configured connections after observing two, and one again returned `status=ok`. It passed
  the wall budget in 2/3 with a 28.174-second median.
- Luna's small 1.681-second median advantage therefore does not justify routing routine EDA work
  to it: the exact-answer failure is much larger than the unstable speed difference. `gpt-5.5`
  remains the correctness baseline until an authenticated Pi comparison proves a better tradeoff.

## 2026-08-29 repeated cross-EDA capability baseline

- Three independent `gpt-5.5` low-reasoning trials passed the exact ADS L1 contract, and three more
  passed the exact AnsysEM L1 contract. Every trial used exactly one Runtime capability call; there
  was no mutation, GUI automation, project access, or solve.
- ADS median wall time was 26.409 s, of which measured Runtime/SSH/Bridge transport was 0.969 s.
  AnsysEM median wall time was 22.285 s, with 1.156 s transport. The remote execution path therefore
  accounted for only about 3.7% and 5.2% of the respective medians; cold Agent/client work remained
  the dominant cost.
- Exact-case selection and variable preflight prevented replaying unrelated lower levels and caught
  missing connection bindings before any Agent process started. The complete 124-test Python suite,
  Ruff, formatting, and all three Pi adapter tests passed before these evaluator-only commits.

## 2026-08-29 Runtime alpha.16 bounded-read acceptance

- The same real ADS `session.status` task returned the same 13-session count with two calls before
  and after adding one deterministic `result_view`; no shell, GUI, mutation, or extra discovery was
  introduced.
- Aggregate model-visible tool payload fell from 9,658 to 2,731 characters, a 71.7% reduction. The
  selected read result itself became the exact 20-character count fact rather than a 13-session
  inventory containing workspace, process, display, and diagnostic fields.
- Wall time varied from 31.062 s to 39.516 s and input tokens from 53,626 to 51,915, so this is
  accepted as a context-pressure improvement rather than a latency claim. Runtime/SSH/ADS time
  remained about 1.1--1.3 s across the two-call lifecycle.
- The complete 115-test Python suite, Ruff, formatting, package build, Twine checks, and all three
  Pi-adapter tests passed. Regression tests preserve native Bridge failures without masking them as
  projection errors and reject missing value/count paths.

## 2026-08-29 Runtime alpha.15 compact-audit and shutdown acceptance

- On 24 real recent calls, compact audit output retained tool, motive, observed client, state,
  timing, and plan-step counts while shrinking from 40,734 to 8,980 characters, a 78.0% reduction.
  The full hash-chained events remain available only through explicit `audit list --full`.
- Review-found duplicate Hook/MCP observations and interleaved request/completion windows are
  covered by regression tests. Compact reads select authoritative Runtime executions and query
  complete recent run groups rather than guessing a fixed event window.
- The Windows descendant-close regression was reproduced twice under independent-review load.
  After the failed-`taskkill` fallback and direct descendant termination were added, 64 concurrent
  stress runs, 50 focused review tests, and the complete 110-test suite passed in the same restricted
  review environment. Normal EOF shutdown and non-Windows behavior remain unchanged.

## 2026-08-29 Runtime alpha.14 canonical-Skill acceptance

- A real Codex-home discovery selected exactly five intended EDA Skills. Runtime resolved to the
  installed alpha.13 plugin while the four directly installed vendor Skills remained canonical.
- Regression tests prove that retained older plugin-cache copies are explicitly disabled and that
  an explicit direct installation outranks even a higher-version cached copy.
- The complete Python suite, Ruff checks, and formatting checks passed before publication.
- After publication, one Codex call created an ADS 2026 Update 2.1 source workspace, applied the
  same structured R/C/GND schematic transaction as the three-call L5 baseline, and freshly reopened
  seven assertions on `display4`. Calls fell from three to one, wall time from 49.435 s to 35.440 s,
  and input tokens from 91,219 to 52,371 while measured Runtime/SSH/ADS time remained 2.510 s.
- The source and output contained 10 and 11 files; their exact disposable root was realpath-checked,
  removed, and verified absent. No solve, GUI automation, arbitrary code, or customer data was used.

## 2026-08-29 Runtime alpha.13 validated-plan acceptance

- All Python tests and Ruff checks passed after three independent review rounds. The review-found
  target-specific capability, durable identity, idempotency, interruption, and audit aggregation
  defects are retained as regression tests.
- The Pi adapter exposes the same ten Runtime tools as Codex, including `eda.run_plan`; its Node
  client tests passed against the candidate Runtime package.
- On the configured remote `display4` profile, one Codex call created a disposable AEDT 2026.1
  HFSS 3D Layout project, waited for three durable jobs, freshly inspected the saved Bundle, and
  exported a verified 800 x 600 PNG. It did not solve, use GUI automation, or access customer data.
- Compared with the prior seven-call lifecycle, the one-call plan reduced input tokens from 165,016
  to 49,300 and Agent/client time from 51.079 s to 37.648 s while Runtime/SSH/AEDT time remained
  comparable at 67.985 s versus 66.297 s.
- The exact scratch project, AEDB, results directory, and PNG were realpath-checked under the
  evaluation root, verified, and removed after measurement.

## 2026-08-29 Runtime alpha.12 matrix acceptance

- The published package, local Codex plugin, Agent-host Runtime, and both isolated remote Bridge
  environments reported alpha.12 after exact-version installation. The repository passed 86 tests,
  Ruff, formatting, build, Twine, trusted publication, and published-wheel verification.
- One matrix command sequentially ran L0 connection discovery plus ADS and AnsysEM L1 capability
  cases. All three passed with exactly one allowed tool call each and no target crossover.
- The three independent Codex sessions took 19.0, 18.2, and 16.0 seconds, about 53.3 seconds total.
  Their Runtime calls totaled about 1.8 seconds, again locating most elapsed time in fixed Agent
  startup and context rather than SSH or either Bridge.
- A matched L0 comparison used 82,899 input tokens under the ordinary global Codex configuration
  and 36,224 under the five-Skill EDA profile, a 56.3% reduction with the same one-call result.
  Wall time was 20.5 versus 22.3 seconds, so the narrow profile is claimed as context and token
  economy, not as a reliable latency reduction.
- The same matrix classified the Pi startup boundary as `agent_auth_unavailable` in about 0.5
  seconds with zero tool calls. The Pi profile installer preserved the credential-file hash and
  correctly reported `login_required`; it did not copy or synthesize another Agent's credentials.

## 2026-08-29 Runtime alpha.11 evidence-safe comparison acceptance

- The repository passed 80 tests, Ruff, formatting, package build, Twine checks, trusted PyPI
  publication, and exact-version installation. Local Runtime and both isolated remote Bridge
  environments reported `0.1.0a11`.
- Fresh Codex capability cases passed with exactly one tool call each. ADS advertised seven
  operations and AnsysEM fourteen. End-to-end Agent time was 20.2 and 18.8 seconds while the
  corresponding Runtime/SSH/Bridge calls took about 0.8 and 1.1 seconds.
- Matched `low` versus `medium` Codex runs did not show a latency benefit: minimal discovery took
  17.9 versus 15.4 seconds, and a two-call ADS read took 22.5 versus 22.3 seconds. Both paths were
  correct, so reasoning level is now recorded as a comparison control rather than advertised as a
  speed switch.
- Reanalysis of 150 historical calls with stable-session scoping retained eight directly proven
  idempotent replays but withdrew thirty cross-task discovery repetitions previously labeled
  potentially redundant. Fourteen same-session status polls remained, totaling about 0.8 seconds
  of conservatively avoidable Runtime time.
- Narrow Codex profile regeneration enabled five current EDA Skills and disabled 204 unrelated
  Skills. Hidden managed backups were excluded and all four installed vendor Skill entrypoints
  matched their repository sources.

## 2026-08-29 bounded documentation-evidence evaluation

- New ADS and AnsysEM L4 cases each completed capability discovery, documentation query, and one
  focused source expansion in exactly three safe Runtime calls. Neither case opened EDA, mutated a
  project, used customer data, or retained document text in its normalized result.
- ADS found three sources and returned a 1,307-character focused passage; AnsysEM found three and
  returned the requested 2,000 characters. The scorer independently retained only aggregate
  response character counts to prove substantive tool responses without trusting the Agent summary.
- Before Bridge optimization, ADS returned 14,455 aggregate response characters and AnsysEM 5,095.
  Compact ADS candidate evidence reduced its retest to 9,025 characters, a 37.6% reduction, while
  preserving the same selected-evidence result. End-to-end ADS latency did not improve in this
  sample, so the result is claimed as context reduction rather than model-speed improvement.

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
