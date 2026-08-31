# Codex EDA profile

This optional Agent-host helper generates one narrow Codex profile for EDA work. It uses Codex's
native profile and per-Skill enablement settings; it does not create another execution path.

The generated profile keeps the Runtime, ADS, AnsysEM, and their documentation Skills enabled and
disables unrelated discovered Skills—including bundled `.system` Skills—only for
`codex --profile eda-runtime`. Other hidden backup directories remain undiscovered. It disables general
plugin discovery, declares the single Runtime MCP directly, and preserves the Runtime's two Codex
audit hooks inline. The user's ordinary Codex configuration remains unchanged. Browser, Apps,
Computer Use, memory injection, multi-agent, and shell snapshotting are disabled in this profile
because normal EDA work uses the Runtime MCP. The Codex `shell_tool` and Agent-visible `code_mode`
features are also disabled, while the internal `code_mode_host` remains enabled because Codex 0.151
uses it for direct MCP transport. A prompt therefore cannot probe EDA through commands or JavaScript
when the Runtime tool set is empty or the task should stop for clarification. The ordinary Codex
profile keeps its normal execution tools.
The installer also discovers MCP servers inherited from the user's global Codex config and disables
all of them inside this profile except `eda-bridge-runtime`. This is generated isolation, not a
hard-coded list: adding another general-purpose MCP globally cannot silently expand the EDA profile.
By default the generated MCP and audit-hook commands use the Python interpreter running the
installer with `-m eda_bridge_runtime.cli`. This avoids keeping the replaceable Windows
`eda-runtime.exe` console-script open during a package upgrade. `--runtime-command` remains an exact
executable override for administrators who intentionally manage a different launch path.

```powershell
eda-runtime agent-profile codex install
codex exec --profile eda-runtime "Inspect the selected EDA target"
```

The repository `install_profile.py` remains a thin compatibility wrapper around the same packaged
implementation; it is not a second installer.

Regenerate the profile after installing or removing Skills. Engineers do not maintain the generated
path list by hand. Hidden backup and archive directories are ignored so historical
Skill copies cannot re-enter the Agent prompt. If several visible plugin releases expose the same
Skill name, exactly one canonical source is enabled: a direct installation wins, otherwise the
highest semantic plugin version is selected and older cache entries remain disabled.

For a self-contained typed execution or evaluation whose complete operation plan is already known,
generate a second Runtime-only profile rather than loading interpretation-oriented vendor Skills:

```powershell
eda-runtime agent-profile codex install `
  --profile-name eda-runtime-eval `
  --keep-name eda-runtime-control
```

This is an administrator/evaluator profile, not another engineer-facing workflow. Keep the normal
five-Skill `eda-runtime` profile for natural-language target interpretation and documentation work.

For a separately authorized unattended evaluation, generate a different
profile with `--approve-mutations`. It pre-approves only the typed Runtime
`eda.submit` and `eda.run_plan` tools; it does not disable the sandbox, approve shell commands, or
change the ordinary `eda-runtime` profile.
