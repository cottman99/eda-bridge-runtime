# Native execution core acceptance — 2026-10-23

Validated versions: Runtime 0.2.0a1, ADS Bridge 0.2.0a1, AnsysEM Bridge 0.3.0a1.
This acceptance records the breaking native execution release.

The new execution path accepts ordinary official Python through
`native.execute` / `eda.native-program/v1`. Runtime owns resource admission,
request identity, jobs, process supervision and evidence. Each Bridge owns its
official SDK, target/session binding and documentation. A single Bridge installs
without requiring the other one.

| Acceptance | Observed result |
| --- | --- |
| Windows Python regressions | Runtime 210, ADS 239, AnsysEM 161 passed |
| Linux Python regressions | Runtime 210, ADS 238, AnsysEM 161 passed; one Windows PowerShell installer test skipped by platform |
| Pi integration | 7 passed; installed profile exposes 12 Runtime tools |
| Independent installation | Runtime only, ADS only, AnsysEM only and both passed dependency and import checks |
| Linux ADS DE background | Official resistor API saved 75 Ohm; fresh process readback matched |
| Linux ADS DE live | Exact captured session saved/read back 90 Ohm; session remained alive |
| Linux ADS DDS | Background creation and exact live page editing passed native readback |
| Linux AEDT 2026 R1 | Background variable 2mm passed fresh reopen; live variable 4mm passed same-session readback |
| Linux PyEDB | Offline variable 3mm passed save and fresh reopen |
| Installed wheels over SSH | ADS, AEDT and PyEDB native observations survived client disconnect; same-key requests reused the job; changed requests returned `idempotency_conflict` |
| Windows ADS 2026 Update 2 | Background official API mutation and fresh-process readback passed |
| Windows AEDT 2026 R1 | Background variable 2mm passed fresh reopen; live variable 4mm passed exact-session readback; a separate process read both saved values after session release |
| Windows PyEDB | Offline variable 3mm passed save and fresh reopen; source preserved |
| Windows profile launch | A real redirected-stdio regression failed before the fix and passed after preserving the original process handles; the configured local MCP connection passed live execution |
| Documentation cold start | 405 synthetic HTML documents: first bounded batch returned partial, detached preparation reached ready; original files remained unchanged |
| SDK knowledge | ADS and PyEDB source signatures/docstrings were retrieved without importing the source or invoking getters |

Concurrency and failure tests cover two clients targeting the same project,
same-key conflict detection, no expiry takeover, stale admission rejection,
queued cancellation, owned-worker cancellation/deadlines, bounded output and
failure-stage retention. An observe declaration does not bypass native job
admission. Partial or absent knowledge is a completed knowledge observation,
not an execution denial.

The old native modules/schema, raw ADS execution switches, import allowlists,
trimmed builtins and POSIX-only native deadline implementation are absent from
the new wheels. Existing compiled workflows keep their SDK implementation and
enter the same Runtime resource/evidence boundary. Markdown is optional advice.

Acceptance uses disposable engineering data. Existing user GUI processes were
preserved; only task-owned acceptance processes were closed. Loaded older GUI
addons take the new code on their next normal launch. An already-running Agent
client may need to reconnect its plugin to discover the new tool list.

The initial Windows Ansys failure was superseded by a successful retest after
refreshing the vendor environment. The Agent host did not inherit installation
and license variables; the verified private runtime profile now supplies them.
Its Windows process launcher also preserves redirected Runtime protocol pipes.
Earlier failure receipts remain available as history. These results establish
the named modes and examples; other AEDT products and exhaustive official API
coverage are not claimed.

Release review added regressions for duplicate-worker orphan recovery, relative-path source fingerprints and undeclared artifact publication. Pi integration now verifies the current 12-tool server, including cancellation. CI covers Windows and Linux; public dependency installation is verified after Runtime publication.
