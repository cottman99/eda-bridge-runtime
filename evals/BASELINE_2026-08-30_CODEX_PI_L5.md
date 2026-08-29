# Codex and Pi L5 EDA lifecycle acceptance

Date: 2026-08-30

This is a sanitized one-run functional comparison of complete disposable engineering lifecycles.
It is not yet a repeated performance benchmark. Both clients used the same GPT-5.5 model family,
low reasoning, one Runtime plan call, exact registered connections, and independent scratch paths
and idempotency keys.

| Lifecycle | Agent | Result | Calls | Jobs | Wall | Runtime + transport + EDA | Outside transport | Input tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ADS create -> structured copy -> fresh reopen | Codex | passed | 1 | 0 | 34.957 s | 2.421 s | 32.536 s | 66,768 |
| ADS create -> structured copy -> fresh reopen | Pi | passed | 1 | 0 | 18.815 s | 2.594 s | 16.221 s | 5,102 |
| AnsysEM create -> fresh inspect -> verified image | Codex | passed | 1 | 3 | 92.325 s | 66.281 s | 26.044 s | 47,595 |
| AnsysEM create -> fresh inspect -> verified image | Pi | passed | 1 | 3 | 86.025 s | 69.156 s | 16.869 s | 6,286 |

Both ADS results preserved the source, freshly reopened the three-instance output, and passed all
seven assertions. Both AnsysEM results created one complete Bundle, freshly inspected it, and
verified the exported image without solving.

The single-run evidence supports three bounded conclusions:

1. Pi can autonomously complete the same L5 workflows as Codex; it is not limited to discovery or
   read-only assistance.
2. In ADS, Agent/client time still dominates. Pi reduced total wall time by 46.2%, while the actual
   Runtime/transport/ADS boundary stayed near 2.5 seconds for both clients.
3. In AnsysEM, roughly 66-69 seconds belongs to the AEDT lifecycle. Pi reduced the remaining
   Agent/client portion, but total wall improvement was only 6.8%. Optimizing SSH cannot remove the
   dominant AEDT save/reopen/image-export cost.

The first Pi ADS run exposed an evaluator-only alias bug: successful `eda_run_plan` was scored as
unexpected `eda.run.plan`. The EDA lifecycle itself passed. The canonical-name fix is covered by a
regression test, and a fresh independent run then passed. All owned remote scratch was removed
after exact-path verification; durable Runtime audit facts remain available.
