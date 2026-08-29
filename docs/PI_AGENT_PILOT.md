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

The Agent host currently uses Node `24.20.0`, npm `11.19.0`, and pinned Pi
`@mariozechner/pi-coding-agent@0.73.1`. The dedicated profile lives outside the repository and
contains no credentials. Its launcher disables all built-in tools and automatic global Skill
discovery, then explicitly loads only three Skills: Runtime control, ADS operation, and AnsysEM
operation. The engineer still starts one command and uses natural language; Pi selects the Skill.

The checked-in package is `integrations/pi-eda-runtime`. It registers exactly seven `eda_*` tools,
maintains one persistent `eda-runtime mcp serve` child, and adds `/eda-runtime-status`. It does not
contain SSH or vendor logic. Pi supplies provider, model, reasoning, session, and tool-call identity
directly from its extension context; Runtime stores these as declared facts and stores MCP client
identity as observed fact.

Measured acceptance on the Agent host:

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

The normal EDA profile deliberately excludes all built-in tools through the launcher because Pi
0.73.1 does not expose a `defaultTools` settings key. A separate maintenance launch may enable
them when developing adapters; ordinary model operations do not receive an alternate shell route
around Runtime.

## Stage 2: one thin Pi package

The reviewed Pi package in this repository contains:

- a native Pi extension that exposes only the seven Runtime tools;
- the Runtime control Skill and references to selected vendor Skills;
- optional Pi lifecycle enrichment; the Runtime already records the mandatory base facts;
- a small status view for active connection, Run state, and elapsed time.

The extension launches `eda-runtime mcp serve` internally. Engineers do not
install a generic third-party MCP bundle or maintain MCP JSON by hand merely for this pilot.

Pi exposes session, provider, model, and reasoning metadata to child commands. The extension may
enrich the Runtime actor contract with those observed values, while the Runtime always retains the
Agent's concise `purpose`, MCP client identity, timing, and linked Run. Missing fields remain
`unknown`; the extension must not parse the transcript to reconstruct them.

## Stage 3: pending A/B acceptance before broader use

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
