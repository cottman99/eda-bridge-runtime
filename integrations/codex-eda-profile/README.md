# Codex EDA profile

This optional Agent-host helper generates one narrow Codex profile for EDA work. It uses Codex's
native profile and per-Skill enablement settings; it does not create another execution path.

The generated profile keeps the Runtime, ADS, AnsysEM, and their documentation Skills enabled and
disables unrelated discovered Skills only for `codex --profile eda-runtime`. It disables general
plugin discovery, declares the single Runtime MCP directly, and preserves the Runtime's two Codex
audit hooks inline. The user's ordinary Codex configuration remains unchanged. Browser, Apps,
Computer Use, memory injection, multi-agent, and shell snapshotting are disabled in this profile
because normal EDA work uses the Runtime MCP.

```powershell
python integrations/codex-eda-profile/install_profile.py `
  --codex-home "$env:USERPROFILE\.codex"
codex exec --profile eda-runtime "Inspect the selected EDA target"
```

Regenerate the profile after installing or removing Skills. Engineers do not maintain the generated
path list by hand.
