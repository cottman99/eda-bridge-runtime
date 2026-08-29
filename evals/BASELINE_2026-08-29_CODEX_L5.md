# Codex L5 EDA lifecycle baseline

Date: 2026-08-29

This is a sanitized, single-run baseline for the first complete disposable
engineering lifecycles. It records normalized measurements only. No raw Agent
trace, private path, customer artifact, or documentation passage is retained.

## Configuration

- Agent: Codex, `gpt-5.5`, medium reasoning, narrow `eda-runtime` profile
- Runtime: direct baselines used `0.1.0a12`; AnsysEM and ADS one-call plans used `0.1.0a13`
  and `0.1.0a14`, respectively
- ADS Bridge: `0.1.0a36`, ADS 2026 Update 2.1, `DISPLAY=:4.0`
- AnsysEM Bridge: `0.2.0a4`, AEDT 2026.1, `DISPLAY=:4.0`
- Solve: forbidden in both cases

## Normalized results

| Case | Result | Calls | Jobs | Wall | Runtime + SSH + Bridge/EDA | Outside transport | Transport share | Input tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ADS blank workspace -> structured copied schematic -> fresh reopen | passed | 3 | 0 | 49.435 s | 2.593 s | 46.842 s | 5.245% | 91,219 |
| Same ADS lifecycle through one validated plan | passed | 1 | 0 | 35.440 s | 2.510 s | 32.930 s | 7.082% | 52,371 |
| AnsysEM project create -> fresh Bundle inspect -> verified AEDT image | passed | 7 | 3 | 117.376 s | 66.297 s | 51.079 s | 56.483% | 165,016 |
| Same AnsysEM lifecycle through one validated plan | passed | 1 | 3 | 105.633 s | 67.985 s | 37.648 s | 64.359% | 49,300 |

The cases deliberately follow each product's native execution model and are
not identical workloads. They compare orchestration quality and measurement
boundaries, not ADS versus AEDT product speed.

## Findings

1. The direct Agent/client portion was similar in absolute time: about 47-51 seconds. Validated
   plans reduced it to about 33-38 seconds without weakening the EDA work.
2. ADS Bridge work was already small relative to the Agent. More SSH tuning
   cannot materially improve this case.
3. The AnsysEM lifecycle contains real AEDT process, save, fresh-reopen, durable
   job, inspection, and image-export cost. Its measured EDA path therefore
   dominates more than half of the wall time.
4. Both cases completed without arbitrary code, GUI gestures, solve, customer
   data, blind replay, or retained disposable artifacts.
5. The dedicated Pi profile is now authenticated and has passed matching L5 one-call lifecycles.
   The cross-client results are recorded separately in
   `BASELINE_2026-08-30_CODEX_PI_L5.md`; the earlier missing-authentication result remains excluded
   from Bridge and EDA reliability.
6. The validated plan reduced Agent calls by 85.7%, input tokens by 70.1%, Agent/client time by
   26.3%, and total wall time by 10.0%. Runtime/SSH/AEDT time changed by only +2.5%, confirming that
   the gain came from removing repeated model turns rather than weakening the EDA lifecycle.
7. The matching ADS plan reduced Agent calls by 66.7%, input tokens by 42.6%, Agent/client time by
   29.7%, and total wall time by 28.3%. Runtime/SSH/ADS time changed by only -3.2%; the source and
   non-overwriting output contained 10 and 11 files before their verified scratch cleanup.
