# Authenticated Codex/Pi read and documentation baseline

Date: 2026-08-30

This stage increases difficulty beyond capability discovery. It covers one
typed live ADS state read and two documentation workflows in which the Agent
must issue a bounded query, choose one returned source, and retrieve one
focused passage. Passage text and raw Agent streams are never retained.

## Post-fix results

| Case | Codex pass | Pi pass | Codex median | Pi median | Pi wall reduction | Codex reported input | Pi reported input |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ADS typed session count | 3/3 | 3/3 | 21.955 s | 10.868 s | 50.5% | 36,751 | 2,368 |
| ADS query -> selected source -> focused evidence | 3/3 | 3/3 | 23.118 s | 13.978 s | 39.5% | 53,433 | 4,823 |
| AnsysEM query -> selected source -> focused evidence | 3/3 | 3/3 | 23.724 s | 13.970 s | 41.1% | 49,667 | 4,204 |

The token columns are provider-reported counters, not asserted billing units.

## Defect found and generalized fix

Before the retained post-fix ADS documentation sample, one Pi trial put the
explicit connection identifier `ads-display4` into the generic `eda` selector.
Runtime correctly rejected it before contacting ADS. The fields had both been
plain optional strings, so this was an avoidable interface ambiguity rather
than an EDA or documentation failure.

Runtime MCP and the Pi adapter now describe the distinction mechanically:

- `connection_id` is an exact registered name and is the field to use when a
  request names a connection;
- `eda` is a vendor type and is allowed only when exactly one registered
  connection has that type.

With no task-specific prompt change, Pi then passed the ADS documentation case
3/3. This is evidence that precise tool schemas can remove Agent errors more
cleanly than adding more natural-language policy.

## Current interpretation

Pi remains materially faster and lighter through source-selection tasks, not
only trivial one-call reads. Both Agents chose acceptable version-matched ADS
and AnsysEM evidence under the exact same deterministic gates. The next useful
boundary is mutation and fresh-reopen validation; these results alone do not
establish engineering design judgment or full lifecycle parity.
