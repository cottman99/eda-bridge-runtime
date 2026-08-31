# Pi EDA Runtime adapter

This is one thin Pi package over EDA Bridge Runtime. It registers exactly ten `eda_*` tools and
one local status command. It contains no SSH routing, EDA API knowledge, retry engine, job store, or
audit database.

Requirements:

- Pi Agent `0.84.4` or compatible;
- `eda-runtime` on the Agent host path;
- Runtime connections already registered for the intended local or SSH EDA workers.

Create or refresh a dedicated profile with the installed Runtime CLI. The installer owns only the
work launcher, sibling `*-login.cmd` and `*-status.cmd` launchers, bounded settings, and session directory. It neither
creates nor modifies `auth.json`, and verifies an existing credential file is byte-for-byte
unchanged. Run the login launcher and use Pi's `/login` once; it loads no EDA extension, Skill,
tool, or project context. Authentication remains an interactive Pi action. Run the status launcher
to verify the isolated profile directly; checking the user's default Pi profile is not evidence that
the EDA profile is authenticated.

```powershell
eda-runtime agent-profile pi install `
  --profile-dir F:\EDA\pi-eda-agent\config `
  --session-dir F:\EDA\pi-eda-agent\sessions `
  --launcher F:\EDA\pi-eda.cmd `
  --node D:\node\node.exe `
  --pi-cli F:\EDA\pi\node_modules\@earendil-works\pi-coding-agent\dist\bundle\cli.js `
  --vendor-skill F:\skills\ads-agent-bridge\SKILL.md `
  --vendor-skill F:\skills\ansysem-agent-bridge\SKILL.md
```

No Runtime source checkout is required. The repository `install_profile.py` is only a thin
compatibility wrapper around the packaged implementation.

Try it without installing:

```powershell
$env:PI_CODING_AGENT_DIR = 'F:\EDA\pi-eda-agent\config'
pi --offline -e F:\path\to\eda-bridge-runtime\integrations\pi-eda-runtime
```

The generated launcher always loads this Runtime extension and its Runtime Skill. Installer-selected
vendor Skills are loaded into the same one-command profile; the engineer does not choose them on
each task. The normal profile keeps only Pi's built-in read tool; shell/write/edit remain disabled,
and every EDA action still uses Runtime.

The launcher also injects the Python interpreter running the installer. The persistent Pi client
starts `python -m eda_bridge_runtime.cli mcp serve`, so a Windows package upgrade does not depend on
replacing an open `eda-runtime.exe` console-script. Use `--runtime-command` only for an intentional
exact executable override.
