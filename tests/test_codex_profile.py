import importlib.util
from pathlib import Path


def load_installer():
    path = Path(__file__).parents[1] / "integrations" / "codex-eda-profile" / "install_profile.py"
    spec = importlib.util.spec_from_file_location("codex_eda_profile", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_skill(root: Path, folder: str, name: str) -> Path:
    path = root / folder / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    return path.resolve()


def test_profile_disables_unrelated_skills_without_changing_global_config(tmp_path):
    installer = load_installer()
    keep = write_skill(tmp_path / "skills", "ads", "ads-agent-bridge")
    disable = write_skill(tmp_path / "skills", "other", "unrelated")
    global_config = tmp_path / "config.toml"
    global_config.write_text('model = "unchanged"\n', encoding="utf-8")

    output, enabled, disabled = installer.install_profile(
        tmp_path, runtime_command="D:/runtime/eda-runtime.exe"
    )
    profile = output.read_text(encoding="utf-8")

    assert enabled == 1
    assert disabled == 1
    assert f"path = {installer.json.dumps(str(keep))}" in profile
    assert f"path = {installer.json.dumps(str(disable))}" in profile
    assert "enabled = true" in profile
    assert "enabled = false" in profile
    assert "plugins = false" in profile
    assert '[mcp_servers."eda-bridge-runtime"]' in profile
    assert 'command = "D:/runtime/eda-runtime.exe"' in profile
    assert "eda-runtime hook codex-pre-tool-use" in profile
    assert "eda-runtime hook codex-post-tool-use" in profile
    assert global_config.read_text(encoding="utf-8") == 'model = "unchanged"\n'


def test_unattended_profile_approves_only_typed_runtime_mutation(tmp_path):
    installer = load_installer()
    write_skill(tmp_path / "skills", "ads", "ads-agent-bridge")

    output, _, _ = installer.install_profile(tmp_path, approve_mutations=True)
    profile = output.read_text(encoding="utf-8")

    assert '[mcp_servers."eda-bridge-runtime".tools."eda.submit"]' in profile
    assert '[mcp_servers."eda-bridge-runtime".tools."eda.run_plan"]' in profile
    assert 'approval_mode = "approve"' in profile
    assert "dangerously-bypass" not in profile


def test_profile_ignores_hidden_skill_backups(tmp_path):
    installer = load_installer()
    current = write_skill(tmp_path / "skills", "ads", "ads-agent-bridge")
    hidden = write_skill(tmp_path / "skills", ".ads-agent-backups/ads-old", "ads-agent-bridge")

    discovered = installer.discover_skills(tmp_path)

    assert (current, "ads-agent-bridge") in discovered
    assert (hidden, "ads-agent-bridge") not in discovered
