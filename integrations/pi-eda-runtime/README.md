# Pi EDA Runtime adapter

This is one thin Pi package over EDA Bridge Runtime. It registers exactly eight `eda_*` tools and
one local status command. It contains no SSH routing, EDA API knowledge, retry engine, job store, or
audit database.

Requirements:

- Pi Agent `0.84.4` or compatible;
- `eda-runtime` on the Agent host path;
- Runtime connections already registered for the intended local or SSH EDA workers.

Try it without installing:

```powershell
$env:PI_CODING_AGENT_DIR = 'F:\EDA\pi-eda-agent\config'
pi --offline -e F:\path\to\eda-bridge-runtime\integrations\pi-eda-runtime
```

The normal profile keeps only Pi's built-in read tool so selected Skills are visible and loadable;
shell/write/edit remain disabled. Vendor Skills may be selected alongside the bundled Runtime
Skill, but every EDA action still uses Runtime.
