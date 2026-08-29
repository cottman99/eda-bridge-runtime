# Agent and EDA evaluations

These developer evaluations compare Agent clients through one unchanged Runtime contract. They are
not part of the Runtime kernel or the end-user workflow.

Cases progress from Runtime-only discovery to Bridge reads, disposable EDA mutations, durable-job
resume/idempotency, and bounded engineering workflows. Every case declares allowed tools, exact
deterministic gates, budgets, and safety limits. The Agent executes the task; `run_case.py` scores it.

Raw Agent streams may contain local target facts and are not saved unless `--raw-output` is supplied.
Normalized results contain only cross-client metrics with matching definitions, the canonical tool
sequence, non-sensitive Run/job/deduplication counts, a final compact result, and the raw trace hash.
This lets mutation cases prove idempotency from Runtime responses instead of trusting the Agent's
summary. Client-specific notions such as a Codex
user turn versus a Pi assistant message are not mislabeled as one comparable metric. Never commit
real-host raw streams or customer artifacts.

```powershell
python evals/run_case.py --case evals/cases/l0_connections.json `
  --agent codex --model gpt-5.5
```

Pi uses the checked-in thin adapter and the same case prompt. Authentication remains in the private
Agent profile and is never copied into a case or result.

`summarize_results.py` combines only normalized results. It omits every Agent
final payload and raw trace, distinguishes authentication from Runtime/EDA
failure, and only calls a case cross-Agent comparable when more than one Agent
actually passed that same case.
