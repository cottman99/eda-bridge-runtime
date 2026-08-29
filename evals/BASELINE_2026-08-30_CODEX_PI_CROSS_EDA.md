# Codex and Pi one-turn cross-EDA acceptance

Date: 2026-08-30

This sanitized three-trial-per-Agent comparison asks one Agent turn to coordinate two exact vendor
connections. Trials were interleaved. Each uses one ADS plan and one AnsysEM plan; Runtime does not
pretend they form one cross-vendor transaction.

| Agent | Result | Runtime calls | Projected runs | Jobs | Wall | Runtime + transport + EDA | Outside transport | Input tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | 3/3 passed | 2 each | 5 each | 3 each | 103.691 s median | 66.765 s median | 36.113 s median | 70,205 median |
| Pi | 3/3 passed | 2 each | 5 each | 3 each | 92.718 s median | 64.954 s median | 26.880 s median | 8,419 median |

All six trials preserved and freshly reopened the three-instance ADS design with seven assertions,
then created, freshly inspected, and exported verified evidence for one AnsysEM Bundle. None ran a
solver.

Compared with the independent repeated ADS and AnsysEM L5 medians, one-turn coordination reduced
total wall time by about 14.3% for Codex and 9.7% for Pi. The useful pattern is simple: batch
already-known independent engineering work into one Agent turn, but retain one native plan and one
failure boundary per EDA product. A new cross-vendor Runtime transaction is unnecessary.

The first Codex trial stopped after AnsysEM project submission because the case text ambiguously
placed `wait` next to vendor payload fields. Runtime correctly returned `waiting`; Codex did not
claim success. Pi inferred the intended step-level field, but that is not a reliable contract. The
case was corrected to state that `wait` is a plan-step field and is forbidden inside vendor
payload. Both fresh independent reruns then passed. This is retained as evidence that structural
field semantics are more reliable than relying on Agent interpretation.

The repeated aggregate-only baseline is stored in
`evals/baselines/codex-pi-gpt55-low-runtime-a23-l6-cross-eda-repeated-20260830.json`.
