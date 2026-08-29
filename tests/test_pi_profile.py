import importlib.util
import json
from pathlib import Path


def load_installer():
    path = Path(__file__).parents[1] / "integrations/pi-eda-runtime/install_profile.py"
    spec = importlib.util.spec_from_file_location("pi_eda_profile", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pi_profile_update_preserves_credentials_and_unmanaged_settings(tmp_path):
    installer = load_installer()
    profile = tmp_path / "profile"
    profile.mkdir()
    auth = profile / "auth.json"
    original_auth = b'{"provider":{"type":"oauth","access":"private"}}\n'
    auth.write_bytes(original_auth)
    (profile / "settings.json").write_text('{"theme":"dark"}\n', encoding="utf-8")
    node = tmp_path / "node.exe"
    cli = tmp_path / "cli.js"
    node.write_bytes(b"node")
    cli.write_bytes(b"pi")

    result = installer.install_profile(
        profile_dir=profile,
        session_dir=tmp_path / "sessions",
        launcher=tmp_path / "pi-eda.cmd",
        node=node,
        pi_cli=cli,
    )

    settings = json.loads((profile / "settings.json").read_text(encoding="utf-8"))
    assert auth.read_bytes() == original_auth
    assert settings["theme"] == "dark"
    assert settings["defaultProjectTrust"] == "never"
    assert result["auth_state"] == "configured"
    assert result["auth_unchanged"] is True
    launcher = (tmp_path / "pi-eda.cmd").read_text(encoding="utf-8")
    assert "--no-extensions --extension" in launcher
    assert "pi-eda-runtime" in launcher
    assert "--no-skills --skill" in launcher
    assert "eda-runtime-control" in launcher
    assert "--no-builtin-tools --tools read,eda_context_resolve" in launcher
    assert "eda_read" in launcher
    assert "eda_run_plan" in launcher
    assert launcher.endswith(" %*\n")
    login_launcher = (tmp_path / "pi-eda-login.cmd").read_text(encoding="utf-8")
    assert "--no-extensions --no-skills --no-tools --no-context-files" in login_launcher
    assert "eda-runtime-control" not in login_launcher
    assert result["login_launcher"].endswith("pi-eda-login.cmd")


def test_pi_profile_does_not_create_an_auth_file(tmp_path):
    installer = load_installer()
    node = tmp_path / "node.exe"
    cli = tmp_path / "cli.js"
    node.write_bytes(b"node")
    cli.write_bytes(b"pi")
    profile = tmp_path / "profile"

    result = installer.install_profile(
        profile_dir=profile,
        session_dir=tmp_path / "sessions",
        launcher=tmp_path / "pi-eda.cmd",
        node=node,
        pi_cli=cli,
    )

    assert not (profile / "auth.json").exists()
    assert result["auth_state"] == "login_required"


def test_pi_profile_does_not_treat_an_empty_auth_object_as_configured(tmp_path):
    installer = load_installer()
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "auth.json").write_text("{}\n", encoding="utf-8")
    node = tmp_path / "node.exe"
    cli = tmp_path / "cli.js"
    node.write_bytes(b"node")
    cli.write_bytes(b"pi")

    result = installer.install_profile(
        profile_dir=profile,
        session_dir=tmp_path / "sessions",
        launcher=tmp_path / "pi-eda.cmd",
        node=node,
        pi_cli=cli,
    )

    assert result["auth_state"] == "login_required"


def test_pi_profile_loads_selected_vendor_skills_without_exposing_shell(tmp_path):
    installer = load_installer()
    node = tmp_path / "node.exe"
    cli = tmp_path / "cli.js"
    vendor_skill = tmp_path / "vendor" / "SKILL.md"
    node.write_bytes(b"node")
    cli.write_bytes(b"pi")
    vendor_skill.parent.mkdir()
    vendor_skill.write_text("# Vendor\n", encoding="utf-8")
    launcher = tmp_path / "pi-eda.cmd"

    result = installer.install_profile(
        profile_dir=tmp_path / "profile",
        session_dir=tmp_path / "sessions",
        launcher=launcher,
        node=node,
        pi_cli=cli,
        vendor_skills=(vendor_skill,),
    )

    text = launcher.read_text(encoding="utf-8")
    assert str(vendor_skill.resolve()) in text
    assert result["loaded_skills"] == 2
    assert "--tools read,eda_context_resolve" in text
    assert result["runtime_tools"] == 10
    assert "shell" not in text
    assert "write" not in text
    assert "edit" not in text
