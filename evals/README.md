# Agent and EDA evaluations

These developer evaluations compare Agent clients through one unchanged Runtime contract. They are
not part of the Runtime kernel or the end-user workflow.

Cases progress from Runtime-only discovery to Bridge reads, disposable EDA mutations, durable-job
resume/idempotency, and bounded documentation-evidence workflows. Every case declares allowed tools, exact
deterministic gates, budgets, and safety limits. The Agent executes the task; `run_case.py` scores it.
Level 5 begins complete disposable engineering lifecycles. Direct and one-call-plan ADS cases create a blank source,
applies a code-free structured design plan to a non-overwriting copy, and requires fresh-reopen
evidence plus source preservation rather than accepting an Agent summary.
The AnsysEM case creates and freshly reopens a complete HFSS 3D Layout Bundle, independently
inspects its persisted anchors, and exports a hashed AEDT image artifact without solving.

Raw Agent streams may contain local target facts and are not saved unless `--raw-output` is supplied.
Normalized results contain only cross-client metrics with matching definitions, the canonical tool
sequence, non-sensitive Run/job/deduplication counts, aggregate response character counts, a final
compact result, measured Bridge/SSH transport time, remaining Agent/client-side wall time, and the
raw trace hash. Response text itself is never retained. The non-transport partition is deliberately
named by measurement boundary: it includes Agent startup, reasoning, final rendering, and client
overhead, so it is not mislabeled as pure model inference time.
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

Pi uses the checked-in thin adapter and the same case prompt. Authentication remains in the private
Agent profile and is never copied into a case or result.

`summarize_results.py` combines only normalized results. It omits every Agent
final payload and raw trace, distinguishes authentication from Runtime/EDA
failure, and only calls a case cross-Agent comparable when more than one Agent
actually passed that same case.

`run_matrix.py` runs selected cases sequentially so two Agents never contend for one EDA target.
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
Repetitions stay sequential so they do not create EDA contention.
Mutation cases are skipped unless `--approve-mutations` is explicit. If one Agent lacks
authentication, its remaining cases are skipped immediately rather than repeating the same costly
startup failure; the other Agent continues. Only per-case normalized JSON and one compact matrix
summary are written.
Mutation approval is a two-part gate: the matrix must select the case explicitly and the child
runner receives a separate mutation flag. Codex then uses its client-reviewed approval path; the
runner never silently switches to an unrestricted sandbox or bypasses approval.
Codex and Pi model selectors are separate because Pi requires the provider-qualified
`openai-codex/gpt-5.5` name while Codex accepts `gpt-5.5`.
