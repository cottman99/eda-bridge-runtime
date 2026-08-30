# Agent and EDA evaluations

The current evidence-backed cross-client conclusions are consolidated in
[`BASELINE_2026-08-30_CODEX_PI_SUMMARY.md`](BASELINE_2026-08-30_CODEX_PI_SUMMARY.md).

These developer evaluations compare Agent clients through one unchanged Runtime contract. They are
not part of the Runtime kernel or the end-user workflow.

Cases progress from Runtime-only discovery to Bridge reads, disposable EDA mutations, durable-job
resume/idempotency, and bounded documentation-evidence workflows. Every case declares allowed tools, exact
deterministic gates, budgets, and safety limits. The Agent executes the task; `run_case.py` scores it.

The ladder also contains zero-tool ambiguity guards. These cases prove that a client can stop and
request one blocking engineering decision when target or acceptance criteria are missing. They are
the complement of receipt-required execution cases: zero calls are correct only when the case
explicitly forbids execution, never when an Agent merely claims that requested work was completed.
The level-2 cross-EDA case uses one Agent turn and two exact connections to distinguish multi-product
coordination from two unrelated cold starts without adding a cross-vendor transaction abstraction.
Codex cases expose only the Runtime tools declared in `allowed_tools` and use a generated JSON
Schema that constrains final field names and types without supplying expected values. This keeps
wrong-tool and prose-format noise separate from EDA correctness while preserving genuine no-tool
or wrong-value failures.
The Codex parser treats every non-passive completed or started item as a tool attempt, including
shell commands, file changes, web actions, and newly introduced item types. Only assistant text,
reasoning, and client diagnostic errors are passive. This prevents a non-Runtime probe from being
misreported as a zero-tool safety pass.
Level 5 begins complete disposable engineering lifecycles. Direct and one-call-plan ADS cases create a blank source,
applies a code-free structured design plan to a non-overwriting copy, and requires fresh-reopen
evidence plus source preservation rather than accepting an Agent summary.
The AnsysEM case creates and freshly reopens a complete HFSS 3D Layout Bundle, independently
inspects its persisted anchors, and exports a hashed AEDT image artifact without solving.
Another AnsysEM case exercises the smallest useful candidate-workspace state machine: create one
frozen source, begin one mutable candidate, carry the observed optimistic revision into abort, and
freshly inspect the unchanged source. It creates no promoted output and does not claim reconcile or
geometry coverage.
Level 6 adds one explicitly selected generated-input Momentum solve. Fixture preparation remains
outside the Agent turn; the Agent receives only exact source/output/project variables and must use
one typed Runtime call. The Bridge preserves the source, commits only a verified finite complete
N-port result, and owns solver-tree cleanup.
The same level also includes one-turn cross-EDA coordination. It deliberately uses one validated
plan per exact vendor connection and does not invent a cross-vendor transaction or shared rollback
claim.

Level 7 is the first ordinary-engineer outcome gate. ADS starts from no workspace and reaches a
simulated native dataset, CSV, and freshly reopened multi-page DDS result with rectangular and polar
plots. AnsysEM starts from no project and
reaches a built HFSS 3D Layout stackup, ports, setup, finite five-point S-parameters, and freshly
reopened native report. Each case requires one prevalidated Runtime plan and explicit mutation plus
solve approval. A single trial proves the maintained workflow is functional; it is not enough for a
performance ranking.

Pi prompts are supplied through Pi's native `@file` input and deleted after the run. This avoids the
Windows command-line length ceiling for complete typed plans without granting a file-read tool or
retaining prompt content. When a generated Pi launcher already contains the Runtime extension,
pass `--pi-use-launcher-profile`; injecting a second copy correctly fails on duplicate tool names.

Raw Agent streams may contain local target facts and are not saved unless `--raw-output` is supplied.
Normalized results contain only cross-client metrics with matching definitions, the canonical tool
sequence, non-sensitive Run/job/deduplication counts, aggregate response character counts, a final
compact result, measured Bridge/SSH transport time, remaining Agent/client-side wall time, and the
raw trace hash. Response text itself is never retained. The non-transport partition is deliberately
named by measurement boundary: it includes Agent startup, reasoning, final rendering, and client
overhead, so it is not mislabeled as pure model inference time.
Client completion and Runtime success are separate facts: a completed Codex or Pi tool event whose
Runtime Run is failed/cancelled is retained for timing evidence but is not counted as a succeeded
tool call. Pi's private `details.runtime` and Codex structured content normalize to the same facts.
This lets mutation cases prove idempotency from Runtime responses instead of trusting the Agent's
summary. Client-specific notions such as a Codex
user turn versus a Pi assistant message are not mislabeled as one comparable metric. Never commit
real-host raw streams or customer artifacts.

```powershell
python evals/run_case.py --case evals/cases/l0_connections.json `
  --agent codex --model gpt-5.5 --thinking low
```

`--thinking` is applied to both clients so latency and token comparisons do not silently use
different reasoning budgets.
Use `--no-codex-profile` only for a controlled comparison against the user's global Codex
configuration; normal EDA evaluations retain the narrow profile.
For self-contained typed mutation cases, `--codex-profile eda-runtime-eval` may select an
administrator-generated Runtime-only profile. This avoids loading interpretation-oriented vendor
Skills after the case has already supplied the complete typed plan; it does not replace the normal
five-Skill profile for natural-language tasks.

Pi uses the checked-in thin adapter and the same case prompt. Authentication remains in the private
Agent profile and is never copied into a case or result.
For acceptance of a launcher generated from the public Runtime package, pass
`--pi-use-launcher-profile`. The runner then retains the launcher's installed extension and Skills
instead of injecting a second repository copy, while still restricting visible tools to the case's
`allowed_tools` list.
The matrix runner accepts the same flag and forwards it only to Pi child cases, so installed-profile
comparisons do not require hand-running each case.

`summarize_results.py` combines only normalized results. It omits every Agent
final payload and raw trace, distinguishes authentication from Runtime/EDA
failure, and separately labels a zero-call result whose compact final explicitly
reports that the client tool was unavailable. It only calls a case cross-Agent comparable when more than one Agent
actually passed that same case.

`baselines/` retains sanitized observed references, not raw traces or customer facts.
`compare_baseline.py` compares only the same case, Agent, model, and reasoning budget. It labels
samples below the chosen repetition count as insufficient instead of turning one lucky run into a
regression gate.

`run_matrix.py` runs selected cases sequentially so two Agents never contend for one EDA target.
Within each case it interleaves clients and rotates which client goes first by trial and case. This
reduces cold-start, cache, and transient-host-load bias without introducing parallel EDA contention;
the normalized matrix records the actual execution order.
Use repeatable `--case-id` options to run only named cases; an explicit case selection does not
replay lower levels merely because the selected case has a higher level.
The matrix validates every selected case variable before starting an Agent. A missing connection or
scratch path therefore fails once at the command boundary instead of producing repeated opaque
runner failures; unexpected child failures retain a bounded exit code without storing stderr.
Use `--repetitions 2` through `--repetitions 10` when a bounded repeated sample is needed.
The default remains one run and preserves the original result filenames. Repeated runs receive
explicit trial numbers, while the compact summary reports pass rate and medians by case, Agent,
model, and reasoning level. It reports strict contract pass rate, semantic pass rate, and wall-budget
pass rate separately, so a correct but slow trial is not mislabeled as a functional defect.
Values passed through `--var` may contain `{agent}`, `{trial}`, and `{sequence}`. The matrix expands
only those exact placeholders for each child run, allowing disposable paths and idempotency keys to
remain independent without hand-written command duplication; unrelated braces remain literal.
Repetitions stay sequential so they do not create EDA contention.
Mutation cases are skipped unless `--approve-mutations` is explicit. If one Agent lacks
authentication, its remaining cases are skipped immediately rather than repeating the same costly
startup failure; the other Agent continues. Only per-case normalized JSON and one compact matrix
summary are written.
Mutation approval is a two-part gate: the matrix must select the case explicitly and the child
runner receives a separate mutation flag. Codex then uses its client-reviewed approval path; the
runner never silently switches to an unrestricted sandbox or bypasses approval.
Solver approval is independent. A solve-capable case remains skipped even when disposable
mutations are approved; it must also be selected explicitly and receive `--approve-solves`.
Approving a bounded solve never enables arbitrary commands or changes the case's declared solver
limit.
An empty or entirely skipped matrix exits distinctly instead of reporting vacuous success.
Codex and Pi model selectors are separate because Pi requires the provider-qualified
`openai-codex/gpt-5.5` name while Codex accepts `gpt-5.5`.
