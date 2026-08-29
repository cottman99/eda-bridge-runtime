# Codex and Pi L5 EDA lifecycle acceptance

Date: 2026-08-30

This is a sanitized comparison of complete disposable engineering lifecycles. ADS and AnsysEM each
use three interleaved trials per Agent. Both clients used the same GPT-5.5 model family, low
reasoning, one Runtime plan call, exact registered connections, and independent scratch paths and
idempotency keys.

| Lifecycle | Agent | Result | Calls | Jobs | Wall | Runtime + transport + EDA | Outside transport | Input tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ADS create -> structured copy -> fresh reopen | Codex | 3/3 passed | 1 each | 0 | 30.135 s median | 2.515 s median | 27.620 s median | 50,575 median |
| ADS create -> structured copy -> fresh reopen | Pi | 3/3 passed | 1 each | 0 | 18.548 s median | 2.516 s median | 16.032 s median | 5,222 median |
| AnsysEM create -> fresh inspect -> verified image | Codex | 3/3 passed | 1 each | 3 each | 90.871 s median | 63.719 s median | 26.886 s median | 47,822 median |
| AnsysEM create -> fresh inspect -> verified image | Pi | 3/3 passed | 1 each | 3 each | 84.140 s median | 67.156 s median | 16.984 s median | 6,394 median |

All six ADS trials preserved the source, freshly reopened the three-instance output, and passed all
seven assertions. All six AnsysEM trials created one complete Bundle, freshly inspected it, and
verified the exported image without solving.

The evidence supports three bounded conclusions:

1. Pi can autonomously complete the same L5 workflows as Codex; it is not limited to discovery or
   read-only assistance.
2. In repeated ADS runs, Agent/client time still dominates. Pi reduced median total wall time by
   38.5%, while the actual Runtime/transport/ADS boundary was effectively identical at about 2.5
   seconds. Pi's median provider-reported input count was 10.3% of Codex's.
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
The repeated ADS baseline is stored in
`evals/baselines/codex-pi-gpt55-low-runtime-a23-l5-ads-repeated-20260830.json`.
