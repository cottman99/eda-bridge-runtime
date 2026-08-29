# Pi EDA Runtime adapter

This is one thin Pi package over EDA Bridge Runtime. It registers exactly seven `eda_*` tools and
one local status command. It contains no SSH routing, EDA API knowledge, retry engine, job store, or
audit database.

Requirements:

- Pi Agent `0.73.1` or compatible;
- `eda-runtime` on the Agent host path;
- Runtime connections already registered for the intended local or SSH EDA workers.

Try it without installing:

```powershell
$env:PI_CODING_AGENT_DIR = 'F:\EDA\pi-eda-agent\config'
pi --offline --no-builtin-tools -e F:\path\to\eda-bridge-runtime\integrations\pi-eda-runtime
```

The normal profile intentionally disables Pi's built-in shell/read/write/edit tools. Vendor Skills
may be selected alongside the bundled Runtime Skill, but every EDA action still uses Runtime.
