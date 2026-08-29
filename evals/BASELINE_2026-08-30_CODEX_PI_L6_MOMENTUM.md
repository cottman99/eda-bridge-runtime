# Codex and Pi generated-input Momentum acceptance

Date: 2026-08-30

This repeated comparison is the first evaluation level that performs a real solver execution.
Fixture preparation was outside the Agent turn. Each Agent received an independent source copy,
exact output/project/display/idempotency variables, and one typed Runtime submission. The retained
Runtime a23 sample contains three interleaved trials per Agent.

| Agent | Passed | Median wall | Median outside transport | Median input tokens |
| --- | ---: | ---: | ---: | ---: |
| Codex | 2/3 | 38.814 s | 28.204 s | 46,372 |
| Pi | 3/3 | 21.701 s | 11.361 s | 3,373 |

Every actual solver call preserved the generated input and produced a finite complete 2-port matrix
with 17 frequency points plus non-empty CITI, AFS, and STA artifacts. The historical example's
dataset-export warning was retained separately from the successful S-parameter result. Successful
execution boundaries stayed between 10.079 and 10.750 seconds for both clients. After each run, no
`MomEngine`, wrapper, or Momentum server process remained, and owned scratch was removed after
exact-path checks.

One Codex trial made zero tool attempts but returned a claimed-success object with incorrect
frequency count, artifact count, and warning state. Runtime, SSH, Bridge, and solver were never
entered. The evaluator now classifies this strict pattern as
`agent_reported_unverified_success` instead of a generic system failure. The observation remains in
the 2/3 reliability rate and is not discarded as an outlier.

On median wall time, Pi was 44.1% faster. More importantly, it was 3/3 reliable in this sample. The
nearly identical successful solver boundaries show that Pi did not achieve the difference by using
a weaker simulation. This case demonstrates a useful machine advantage over manual operation: one
bounded request performs source protection, non-overwriting staging, solver-tree ownership,
complete N-port finite-data validation, artifact hashing, warning separation, atomic commit, and
durable audit correlation as one repeatable contract.
