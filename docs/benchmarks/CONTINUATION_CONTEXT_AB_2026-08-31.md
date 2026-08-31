# Continuation Context A/B acceptance — 2026-08-31

## Question

Does a content-bound EDA Context reduce remote transport time, EDA execution
time, or Agent-side rediscovery work?

This is a functional timing snapshot, not a statistical performance claim.
It used non-sensitive scratch projects on Linux virtual display 4, ADS 2026
Update 2.1, AEDT 2026.1, persistent SSH Runtime transport, and no solve.

## Contract

1. Create one new scratch target and retain its returned Context.
2. Path A represents a redundant cold-Agent routine: select the registered
   connection, read capabilities, inspect the Context, then run one read-only
   governed native probe.
3. Path B submits the same native probe directly with the retained Context.
4. Compare tool-call count, client transport time, adapter time, result, source
   preservation, and ledger receipt. Do not include promotional screenshots or
   release work in the timed task.
5. A successful Context may materialize only exact target identity and trusted
   content state. Program, effect, write/artifact scope, transaction policy,
   validation, limits, purpose, and idempotency remain explicit.

## Observations

| Observation | ADS | AnsysEM |
| --- | ---: | ---: |
| Capability call over an already-persistent SSH transport | 32 ms | 47 ms |
| First capability call after a transport reset | 891 ms | not repeated |
| New scratch creation | 750 ms | 42.469 s |
| Governed read-only native probe, Path A | 672 ms | 22.219 s |
| Same probe, direct continuation Path B | 672 ms | 22.594 s |
| Source preserved | yes | yes |
| Solve invoked | no | no |

The two AnsysEM native probe times differ by 0.375 s and should be treated as
ordinary application startup noise. Context reuse does not make AEDT open a
project faster. Its verified benefit is eliminating redundant Agent decisions
and tool calls while preserving exact identity and drift checks.

Persistent SSH has already reduced a capability round trip to tens of
milliseconds. Reintroducing per-command SSH would be a regression, but further
SSH optimization is not the primary opportunity in this workload. AEDT
open/read/close dominates the measured wall time.

## Finding discovered by the acceptance

The real acceptance found three successive contract gaps that unit substitutes
had not exposed:

1. ADS Bridge 0.1.0a43 returned only a general workspace/lifecycle Context from
   `workspace.create`, so the first `native.batch` could not use the advertised
   low-token path.
2. Version 0.1.0a44 returned the separate content-bound Context, but the Adapter
   tried to expand it as a lifecycle record before inspecting its role.
3. Version 0.1.0a45 resolved the role first, but full product-update text from
   the Context and the installation's year selector used different canonical
   spellings.

ADS Bridge 0.1.0a46 closes all three boundaries without adding a scenario
wrapper. `workspace.create` keeps the lifecycle Context and also returns a
private content-bound `continuation_context`; the Adapter resolves it by role,
and the version gate recognizes equivalent year and full product-update
spellings for the same exact selected installation. Other years and update
identities still fail closed. The final real rerun passed both paths, returned
the same program result, and preserved the source workspace fingerprint.

## Interpretation

- Context primarily saves Agent work, token use, and target reconstruction
  errors; it does not remove genuine EDA application work.
- On ADS the native execution component was identical in both final runs. The
  cold-style path still pays for its extra discovery calls; the retained
  Context removes those calls rather than accelerating official ADS Python.
- Persistent transport is working and should remain a shared Runtime primitive.
- Greenfield creation must return a continuation-ready binding. Otherwise the
  first native operation still pays a rediscovery tax.
- Future benchmarks should use at least three native repetitions before making
  percentage speed claims. Functional one-shot runs are still useful for
  finding contract breaks.
