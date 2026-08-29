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

    output, enabled, disabled = installer.install_profile(tmp_path)
    profile = output.read_text(encoding="utf-8")

    assert enabled == 1
    assert disabled == 1
    assert f"path = {installer.json.dumps(str(keep))}" in profile
    assert f"path = {installer.json.dumps(str(disable))}" in profile
    assert "enabled = true" in profile
    assert "enabled = false" in profile
    assert "plugins = false" in profile
    assert '[mcp_servers."eda-bridge-runtime"]' in profile
    assert "eda-runtime hook codex-pre-tool-use" in profile
    assert "eda-runtime hook codex-post-tool-use" in profile
    assert global_config.read_text(encoding="utf-8") == 'model = "unchanged"\n'
