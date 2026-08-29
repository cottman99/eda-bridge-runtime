# Pi EDA Runtime adapter

This is one thin Pi package over EDA Bridge Runtime. It registers exactly ten `eda_*` tools and
one local status command. It contains no SSH routing, EDA API knowledge, retry engine, job store, or
audit database.

Requirements:

- Pi Agent `0.84.4` or compatible;
- `eda-runtime` on the Agent host path;
- Runtime connections already registered for the intended local or SSH EDA workers.

Create or refresh a dedicated profile with `install_profile.py`. The installer owns only the
work launcher, a sibling `*-login.cmd` launcher, bounded settings, and session directory. It neither
creates nor modifies `auth.json`, and verifies an existing credential file is byte-for-byte
unchanged. Run the login launcher and use Pi's `/login` once; it loads no EDA extension, Skill,
tool, or project context. Authentication remains an interactive Pi action.

```powershell
python integrations/pi-eda-runtime/install_profile.py `
  --profile-dir F:\EDA\pi-eda-agent\config `
  --session-dir F:\EDA\pi-eda-agent\sessions `
  --launcher F:\EDA\pi-eda.cmd `
  --node D:\node\node.exe `
  --pi-cli F:\EDA\pi\node_modules\@earendil-works\pi-coding-agent\dist\bundle\cli.js `
  --vendor-skill F:\skills\ads-agent-bridge\SKILL.md `
  --vendor-skill F:\skills\ansysem-agent-bridge\SKILL.md
```

Try it without installing:

```powershell
$env:PI_CODING_AGENT_DIR = 'F:\EDA\pi-eda-agent\config'
pi --offline -e F:\path\to\eda-bridge-runtime\integrations\pi-eda-runtime
```

The generated launcher always loads this Runtime extension and its Runtime Skill. Installer-selected
vendor Skills are loaded into the same one-command profile; the engineer does not choose them on
each task. The normal profile keeps only Pi's built-in read tool; shell/write/edit remain disabled,
and every EDA action still uses Runtime.
