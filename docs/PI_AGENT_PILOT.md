# Pi Agent operating profile for remote EDA work

## Decision

Keep Pi and Codex as interchangeable Agent clients of the same Runtime. Use the isolated Pi EDA
profile as the default for bounded, typed execution after the target and requested outcome are
clear. Keep Codex as the default for ambiguous engineering interpretation, repository development,
and work whose scope must still be discovered. Do not install Pi on the EDA worker merely because
the EDA connection is remote.

This is not a claim that Pi replaces Codex. It is a routing decision backed by repeated acceptance:
Pi reduced wall time and Agent overhead without increasing wrong-target, bypass, duplicate-run, or
incomplete-validation rates in the tested ADS, AnsysEM, solver, and cross-EDA cases. The engineer
does not need to choose an Agent for every command; the host profile or future Harness may apply
this routing policy while both clients retain the same Context and Runtime facts.

Pi is another Agent client of EDA Bridge Runtime:

```text
Engineer -> Pi EDA profile -> thin Pi Runtime extension -> EDA Bridge Runtime
                                                     -> local or SSH connection
                                                     -> vendor Bridge -> EDA
```

The Pi extension is an Agent-client adapter, analogous to the Codex plugin. It is not a new
architecture layer. It must not implement SSH routing, EDA APIs, retries, idempotency, job state,
or a second audit database.

## Implemented operating profile

The generated daily launcher now loads the Runtime extension and the administrator-selected
Runtime/ADS/AnsysEM Skills itself. Engineers run one command and do not repeat extension or Skill
flags. It disables every built-in tool except read while explicitly retaining all eleven Runtime
tools; shell, write, and edit are absent. An authentication-free RPC acceptance observed ten
Runtime tools, two configured EDA connections, and a 181.4 ms status refresh while preserving the
empty credential file unchanged.

The profile installer also emits separate login and authentication-status launchers. The latter
checks the isolated EDA profile with Pi's native `auth check` command before any EDA extension or
Skill is loaded. This prevents a successful login in the user's default Pi profile from being
mistaken for readiness of the isolated EDA profile.

The Agent host currently uses Node `24.20.0`, npm `11.19.0`, and pinned Pi
`@earendil-works/pi-coding-agent@0.84.4`. The dedicated profile lives outside the repository and
contains no credentials in the repository. Its launcher keeps only Pi's read-only file tool,
disables shell/write/edit and automatic global Skill discovery, then explicitly loads five Skills:
Runtime control plus operation and documentation Skills for ADS and AnsysEM. The engineer still
starts one command and uses natural language; Pi selects and reads the relevant Skill.

The canonical adapter source is `integrations/pi-eda-runtime`, and the public Runtime wheel carries
its execution assets so an Agent host does not need this repository checkout. It registers exactly ten `eda_*` tools,
maintains one persistent `eda-runtime mcp serve` child, and adds `/eda-runtime-status`. It does not
contain SSH or vendor logic. Pi supplies provider, model, reasoning, session, and tool-call identity
directly from its extension context; Runtime stores these as declared facts and stores MCP client
identity as observed fact.

Initial alpha.7 acceptance on the Agent host (retained as historical evidence):

- package client test: seven tools plus a registry read passed;
- real Pi RPC load: exactly seven Runtime tools and the three intended Skills were visible after
  global discovery was disabled;
- cold `/eda-runtime-status refresh`: 1013.4 ms;
- second call in the same Pi session: 12.8 ms;
- two registered EDA connections were found without opening EDA or SSH.

## Installation and isolation

- Install a pinned current Pi package on the Agent host.
- Give the EDA profile its own `PI_CODING_AGENT_DIR` and session directory so it does not inherit a
  general-purpose Pi configuration.
- Authenticate interactively with an existing supported subscription first. Do not put API keys in
  settings, scripts, repositories, or Runtime connection records.
- Choose the startup model from Pi's live model catalog after login; do not hard-code a model name
  before the installed catalog is inspected.
- Disable install telemetry for the dedicated profile.

Example profile settings (paths are intentionally generic):

```json
{
  "defaultThinkingLevel": "medium",
  "enableInstallTelemetry": false,
  "quietStartup": true,
  "sessionDir": "D:/EDA/pi-eda-data/sessions",
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 16000
  },
  "retry": {
    "enabled": true,
    "maxRetries": 1,
    "baseDelayMs": 1000,
    "provider": {
      "maxRetries": 0,
      "maxRetryDelayMs": 15000
    }
  }
}
```

The normal EDA profile enables only the built-in `read` tool so Pi can actually load selected
Skills. It does not receive shell, edit, or write as an alternate route around Runtime.

## Thin Pi client package

The reviewed Pi package in this repository contains:

- a native Pi extension that exposes only the eleven Runtime tools;
- the Runtime control Skill and references to selected vendor Skills;
- optional Pi lifecycle enrichment; the Runtime already records the mandatory base facts;
- a small status view for active connection, Run state, and elapsed time.

The extension launches `eda-runtime mcp serve` internally. Engineers do not
install a generic third-party MCP bundle or maintain MCP JSON by hand for normal EDA work.

Pi exposes session, provider, model, and reasoning metadata to child commands. The extension may
enrich the Runtime actor contract with those observed values, while the Runtime always retains the
Agent's concise `purpose`, MCP client identity, timing, and linked Run. Missing fields remain
`unknown`; the extension must not parse the transcript to reconstruct them.

## Promotion evidence

The alpha.8 autonomous retest passed without human correction. Pi read the selected Skill,
discovered the missing operation schema once, reused one mutation idempotency key, waited inside
Runtime, and completed fresh bundle inspection. Compared with the preceding diagnostic run,
tool calls fell from 28 to 7, assistant turns from 29 to 8, processed tokens from 374394 to 59350,
and elapsed time from 158 to 73 seconds.

The promotion ladder ran the same bounded task through Codex and Pi using unchanged Context and
connection contracts. It covered:

1. inspect one target;
2. submit one non-destructive typed operation;
3. disconnect and resume one durable job;
4. intentionally repeat one idempotency key;
5. verify both Runtime and Agent audit hash chains.

The repeated evidence now includes capabilities, status, documentation retrieval, ADS and AnsysEM
mutations with exact idempotent replay, structured design inspection, a real Momentum solve,
candidate begin/abort, and one-turn cross-EDA coordination. The consolidated measurements and
sample counts are maintained in `../evals/BASELINE_2026-08-30_CODEX_PI_SUMMARY.md`.

## Operating safeguards

- A bounded execution is successful only when a Runtime receipt and case-specific validation
  exist. Agent prose alone is not evidence of execution.
- Runtime records calls that reach it. A zero-tool claimed success is a client/evaluator omission,
  so the Agent host or future Harness must reject it; Runtime must not infer a call from chat text.
- Do not automatically retry a mutation after an ambiguous transport failure. Reuse the same
  idempotency key and reconcile the durable Run first.
- Keep vendor failure boundaries separate even when one Agent turn batches ADS and AnsysEM work.
- Route back to Codex or an engineer when target, intent, connectivity, or validation criteria are
  ambiguous. This is task routing, not a different EDA control path.

## Explicit non-goals

- no separate SSH extension for normal EDA work;
- no EDA-specific API knowledge in Pi;
- no duplicate Runtime or Bridge implementation;
- no automatic trust of arbitrary workspaces;
- no uncontrolled third-party Pi packages;
- no claim that Pi is universally better than Codex outside the measured bounded-execution scope.
