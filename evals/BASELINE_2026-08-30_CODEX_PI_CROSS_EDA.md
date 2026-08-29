# Codex and Pi one-turn cross-EDA acceptance

Date: 2026-08-30

This sanitized single-run comparison asks one Agent turn to coordinate two exact vendor
connections. It uses one ADS plan and one AnsysEM plan; Runtime does not pretend they form one
cross-vendor transaction.

| Agent | Result | Runtime calls | Projected runs | Jobs | Wall | Runtime + transport + EDA | Outside transport | Input tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | passed | 2 | 5 | 3 | 101.906 s | 66.233 s | 35.673 s | 71,422 |
| Pi | passed | 2 | 5 | 3 | 90.060 s | 65.047 s | 25.013 s | 8,240 |

Both clients preserved and freshly reopened the three-instance ADS design with seven assertions,
then created, freshly inspected, and exported verified evidence for one AnsysEM Bundle. Neither
ran a solver.

Compared with the sum of the matching independent L5 plan trials, one-turn coordination reduced
total wall time by about 19.9% for Codex and 14.1% for Pi. The useful pattern is therefore simple:
batch already-known independent engineering work into one Agent turn, but retain one native plan
and one failure boundary per EDA product. A new cross-vendor Runtime transaction is unnecessary.

The first Codex trial stopped after AnsysEM project submission because the case text ambiguously
placed `wait` next to vendor payload fields. Runtime correctly returned `waiting`; Codex did not
claim success. Pi inferred the intended step-level field, but that is not a reliable contract. The
case was corrected to state that `wait` is a plan-step field and is forbidden inside vendor
payload. Both fresh independent reruns then passed. This is retained as evidence that structural
field semantics are more reliable than relying on Agent interpretation.
