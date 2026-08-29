# Pi EDA Runtime adapter

This is one thin Pi package over EDA Bridge Runtime. It registers exactly nine `eda_*` tools and
one local status command. It contains no SSH routing, EDA API knowledge, retry engine, job store, or
audit database.

Requirements:

- Pi Agent `0.84.4` or compatible;
- `eda-runtime` on the Agent host path;
- Runtime connections already registered for the intended local or SSH EDA workers.

Create or refresh a dedicated profile with `install_profile.py`. The installer owns only the
launcher, bounded settings, and session directory. It neither creates nor modifies `auth.json`, and
verifies an existing credential file is byte-for-byte unchanged. Authentication remains an
interactive Pi action.

```powershell
python integrations/pi-eda-runtime/install_profile.py `
  --profile-dir F:\EDA\pi-eda-agent\config `
  --session-dir F:\EDA\pi-eda-agent\sessions `
  --launcher F:\EDA\pi-eda.cmd `
  --node D:\node\node.exe `
  --pi-cli F:\EDA\pi\node_modules\@earendil-works\pi-coding-agent\dist\bundle\cli.js
```

Try it without installing:

```powershell
$env:PI_CODING_AGENT_DIR = 'F:\EDA\pi-eda-agent\config'
pi --offline -e F:\path\to\eda-bridge-runtime\integrations\pi-eda-runtime
```

The normal profile keeps only Pi's built-in read tool so selected Skills are visible and loadable;
shell/write/edit remain disabled. Vendor Skills may be selected alongside the bundled Runtime
Skill, but every EDA action still uses Runtime.
