# Pi Agent pilot for remote EDA work

## Decision

Install Pi on the Agent host as an isolated pilot, not as a replacement for Codex and not on the
EDA worker by default. The pilot tests whether a small prompt, a narrow tool set, and native Pi
lifecycle events make routine remote EDA work faster and more predictable.

Pi is another Agent client of EDA Bridge Runtime:

```text
Engineer -> Pi EDA profile -> thin Pi Runtime extension -> EDA Bridge Runtime
                                                     -> local or SSH connection
                                                     -> vendor Bridge -> EDA
```

The Pi extension is an Agent-client adapter, analogous to the Codex plugin. It is not a new
architecture layer. It must not implement SSH routing, EDA APIs, retries, idempotency, job state,
or a second audit database.

## Implemented pilot

The generated daily launcher now loads the Runtime extension and the administrator-selected
Runtime/ADS/AnsysEM Skills itself. Engineers run one command and do not repeat extension or Skill
flags. It disables every built-in tool except read while explicitly retaining all ten Runtime
tools; shell, write, and edit are absent. An authentication-free RPC acceptance observed ten
Runtime tools, two configured EDA connections, and a 181.4 ms status refresh while preserving the
empty credential file unchanged.

The Agent host currently uses Node `24.20.0`, npm `11.19.0`, and pinned Pi
`@earendil-works/pi-coding-agent@0.84.4`. The dedicated profile lives outside the repository and
contains no credentials. Its launcher keeps only Pi's read-only file tool, disables shell/write/edit
and automatic global Skill discovery, then explicitly loads only three Skills: Runtime control,
ADS operation, and AnsysEM operation. The engineer still starts one command and uses natural
language; Pi selects and reads the relevant Skill.

The checked-in package is `integrations/pi-eda-runtime`. It registers exactly nine `eda_*` tools,
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

## Stage 1: isolated local installation

- Install a pinned current Pi package on the Agent host.
- Give the EDA profile its own `PI_CODING_AGENT_DIR` and session directory so it does not inherit a
  general-purpose Pi configuration.
- Authenticate interactively with an existing supported subscription first. Do not put API keys in
  settings, scripts, repositories, or Runtime connection records.
- Choose the startup model from Pi's live model catalog after login; do not hard-code a model name
  before the installed catalog is inspected.
- Disable install telemetry for the pilot.

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

## Stage 2: one thin Pi package

The reviewed Pi package in this repository contains:

- a native Pi extension that exposes only the nine Runtime tools;
- the Runtime control Skill and references to selected vendor Skills;
- optional Pi lifecycle enrichment; the Runtime already records the mandatory base facts;
- a small status view for active connection, Run state, and elapsed time.

The extension launches `eda-runtime mcp serve` internally. Engineers do not
install a generic third-party MCP bundle or maintain MCP JSON by hand merely for this pilot.

Pi exposes session, provider, model, and reasoning metadata to child commands. The extension may
enrich the Runtime actor contract with those observed values, while the Runtime always retains the
Agent's concise `purpose`, MCP client identity, timing, and linked Run. Missing fields remain
`unknown`; the extension must not parse the transcript to reconstruct them.

## Stage 3: A/B acceptance and autonomous retest

The alpha.8 autonomous retest passed without human correction. Pi read the selected Skill,
discovered the missing operation schema once, reused one mutation idempotency key, waited inside
Runtime, and completed fresh bundle inspection. Compared with the preceding diagnostic run,
tool calls fell from 28 to 7, assistant turns from 29 to 8, processed tokens from 374394 to 59350,
and elapsed time from 158 to 73 seconds.

Run the same bounded task through Codex and Pi using one unchanged Context and connection:

1. inspect one target;
2. submit one non-destructive typed operation;
3. disconnect and resume one durable job;
4. intentionally repeat one idempotency key;
5. verify both Runtime and Agent audit hash chains.

Compare total elapsed time, model time, tool-call count, redundant discovery calls, token usage,
retries, task correctness, and engineer interventions. Pi is promoted only if it reduces overhead
without increasing wrong-target, bypass, duplicate-run, or incomplete-validation rates.

## Explicit non-goals

- no separate SSH extension for normal EDA work;
- no EDA-specific API knowledge in Pi;
- no duplicate Runtime or Bridge implementation;
- no automatic trust of arbitrary workspaces;
- no uncontrolled third-party Pi packages;
- no claim that a smaller Agent is better before measured A/B evidence.
