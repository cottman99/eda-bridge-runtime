# Codex and Pi generated-input Momentum acceptance

Date: 2026-08-30

This sanitized single-run comparison is the first evaluation level that performs a real solver
execution. Fixture preparation was outside the Agent turn. Each Agent received exact source,
output, project, display, and idempotency variables and was allowed one typed Runtime submission.

| Agent | Result | Calls | Wall | Runtime + transport + solver | Outside transport | Input tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Codex | passed | 1 | 37.363 s | 10.437 s | 26.926 s | 46,218 |
| Pi | passed | 1 | 21.477 s | 10.406 s | 11.071 s | 3,360 |

Both independent runs preserved the generated input and produced a finite complete 2-port matrix
with 17 frequency points plus non-empty CITI, AFS, and STA artifacts. The historical example's
dataset-export warning was retained separately from the successful S-parameter result. After
verification, no `MomEngine`, wrapper, or Momentum server process remained, and both owned scratch
trees were removed after exact-path checks.

The nearly identical 10.4-second execution boundary shows that both clients reached the same
Bridge and solver path. Pi's 42.5% lower total wall time came from the Agent/client side, not a
faster or weaker simulation. This case also demonstrates a useful machine advantage over manual
operation: one bounded request performs source protection, non-overwriting staging, solver-tree
ownership, complete N-port finite-data validation, artifact hashing, warning separation, atomic
commit, and durable audit correlation as one repeatable contract.
