# Codex and Pi L5 EDA lifecycle acceptance

Date: 2026-08-30

This is a sanitized comparison of complete disposable engineering lifecycles. ADS is a one-run
functional comparison; AnsysEM is a three-trial interleaved reliability sample. Both clients used
the same GPT-5.5 model family, low reasoning, one Runtime plan call, exact registered connections,
and independent scratch paths and idempotency keys.

| Lifecycle | Agent | Result | Calls | Jobs | Wall | Runtime + transport + EDA | Outside transport | Input tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ADS create -> structured copy -> fresh reopen | Codex | passed | 1 | 0 | 34.957 s | 2.421 s | 32.536 s | 66,768 |
| ADS create -> structured copy -> fresh reopen | Pi | passed | 1 | 0 | 18.815 s | 2.594 s | 16.221 s | 5,102 |
| AnsysEM create -> fresh inspect -> verified image | Codex | 3/3 passed | 1 each | 3 each | 90.871 s median | 63.719 s median | 26.886 s median | 47,822 median |
| AnsysEM create -> fresh inspect -> verified image | Pi | 3/3 passed | 1 each | 3 each | 84.140 s median | 67.156 s median | 16.984 s median | 6,394 median |

Both ADS results preserved the source, freshly reopened the three-instance output, and passed all
seven assertions. All six AnsysEM trials created one complete Bundle, freshly inspected it, and
verified the exported image without solving.

The evidence supports three bounded conclusions:

1. Pi can autonomously complete the same L5 workflows as Codex; it is not limited to discovery or
   read-only assistance.
2. In ADS, Agent/client time still dominates. Pi reduced total wall time by 46.2%, while the actual
   Runtime/transport/ADS boundary stayed near 2.5 seconds for both clients.
3. In repeated AnsysEM runs, roughly 62-67 seconds belonged to the Bridge/AEDT lifecycle. Pi reduced
   median Agent/client time by 36.8%, but total wall improvement was 7.4%. Optimizing SSH cannot
   remove the dominant AEDT save/reopen/image-export cost. Pi's median input count was 13.4% of
   Codex's provider-reported count.

The first Pi ADS run exposed an evaluator-only alias bug: successful `eda_run_plan` was scored as
unexpected `eda.run.plan`. The EDA lifecycle itself passed. The canonical-name fix is covered by a
regression test, and a fresh independent run then passed. All owned remote scratch was removed
after exact-path verification; durable Runtime audit facts remain available.

The repeated AnsysEM baseline is stored as aggregate-only evidence in
`evals/baselines/codex-pi-gpt55-low-runtime-a23-l5-ansys-repeated-20260830.json`.
