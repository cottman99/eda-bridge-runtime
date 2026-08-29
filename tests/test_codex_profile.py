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


def test_profile_discovers_official_system_skills_but_not_nested_hidden_backups(tmp_path):
    installer = load_installer()
    system = write_skill(tmp_path / "skills", ".system/openai-docs", "openai-docs")
    hidden = write_skill(tmp_path / "skills", ".system/.backup/openai-docs-old", "openai-docs")

    discovered = installer.discover_skills(tmp_path)

    assert (system, "openai-docs") in discovered
    assert (hidden, "openai-docs") not in discovered


def test_profile_enables_only_latest_cached_version_of_same_skill(tmp_path):
    installer = load_installer()
    cache = tmp_path / "plugins" / "cache" / "runtime" / "eda-runtime"
    old = write_skill(cache / "0.1.0-alpha.12" / "skills", "runtime", "eda-runtime-control")
    current = write_skill(cache / "0.1.0-alpha.13" / "skills", "runtime", "eda-runtime-control")

    output, enabled, disabled = installer.install_profile(tmp_path)
    profile = output.read_text(encoding="utf-8")

    assert enabled == 1
    assert disabled == 1
    assert f"path = {installer.json.dumps(str(old))}\nenabled = false" in profile
    assert f"path = {installer.json.dumps(str(current))}\nenabled = true" in profile


def test_direct_skill_outweighs_newer_plugin_cache_copy(tmp_path):
    installer = load_installer()
    direct = write_skill(tmp_path / "skills", "ads", "ads-agent-bridge")
    cached = write_skill(
        tmp_path / "plugins" / "cache" / "ads" / "ads" / "99.0.0" / "skills",
        "ads",
        "ads-agent-bridge",
    )

    output, enabled, disabled = installer.install_profile(tmp_path)
    profile = output.read_text(encoding="utf-8")

    assert enabled == 1
    assert disabled == 1
    assert f"path = {installer.json.dumps(str(direct))}\nenabled = true" in profile
    assert f"path = {installer.json.dumps(str(cached))}\nenabled = false" in profile


def test_cached_versions_follow_semantic_prerelease_order(tmp_path):
    installer = load_installer()
    cache = tmp_path / "plugins" / "cache" / "runtime" / "eda-runtime"
    alpha = write_skill(cache / "1.0.0-alpha.99" / "skills", "runtime", "eda-runtime-control")
    beta = write_skill(cache / "1.0.0-beta.2" / "skills", "runtime", "eda-runtime-control")
    stable = write_skill(cache / "1.0.0" / "skills", "runtime", "eda-runtime-control")

    output, enabled, disabled = installer.install_profile(tmp_path)
    profile = output.read_text(encoding="utf-8")

    assert enabled == 1
    assert disabled == 2
    assert f"path = {installer.json.dumps(str(alpha))}\nenabled = false" in profile
    assert f"path = {installer.json.dumps(str(beta))}\nenabled = false" in profile
    assert f"path = {installer.json.dumps(str(stable))}\nenabled = true" in profile
