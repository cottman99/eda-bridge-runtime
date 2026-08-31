import json
import sys
from pathlib import Path

from eda_bridge_runtime import cli, pi_profile


def load_installer():
    return pi_profile


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
    assert 'set "EDA_RUNTIME_COMMAND="' in launcher
    assert f'set "EDA_RUNTIME_PYTHON={sys.executable}"' in launcher
    assert launcher.endswith(" %*\n")
    login_launcher = (tmp_path / "pi-eda-login.cmd").read_text(encoding="utf-8")
    assert "--no-extensions --no-skills --no-tools --no-context-files" in login_launcher
    assert "eda-runtime-control" not in login_launcher
    assert result["login_launcher"].endswith("pi-eda-login.cmd")
    status_launcher = (tmp_path / "pi-eda-status.cmd").read_text(encoding="utf-8")
    assert "auth check --provider openai-codex --json" in status_launcher
    assert "eda-runtime-control" not in status_launcher
    assert result["status_launcher"].endswith("pi-eda-status.cmd")
    assert result["auth_provider"] == "openai-codex"
    assert result["runtime_launch"] == "python-module"


def test_pi_profile_preserves_exact_runtime_executable_override(tmp_path):
    node = tmp_path / "node.exe"
    pi_bundle = tmp_path / "cli.js"
    node.write_bytes(b"node")
    pi_bundle.write_bytes(b"pi")
    launcher = tmp_path / "pi-eda.cmd"

    result = pi_profile.install_profile(
        profile_dir=tmp_path / "profile",
        session_dir=tmp_path / "sessions",
        launcher=launcher,
        node=node,
        pi_cli=pi_bundle,
        runtime_command="D:/runtime/eda-runtime.exe",
    )

    text = launcher.read_text(encoding="utf-8")
    assert 'set "EDA_RUNTIME_COMMAND=D:/runtime/eda-runtime.exe"' in text
    assert 'set "EDA_RUNTIME_PYTHON="' in text
    assert result["runtime_launch"] == "executable-override"


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
    assert result["runtime_tools"] == 11
    assert "shell" not in text
    assert "write" not in text
    assert "edit" not in text


def test_pi_profile_rejects_ambiguous_auth_provider(tmp_path):
    installer = load_installer()
    node = tmp_path / "node.exe"
    cli = tmp_path / "cli.js"
    node.write_bytes(b"node")
    cli.write_bytes(b"pi")

    try:
        installer.install_profile(
            profile_dir=tmp_path / "profile",
            session_dir=tmp_path / "sessions",
            launcher=tmp_path / "pi-eda.cmd",
            node=node,
            pi_cli=cli,
            auth_provider="openai codex",
        )
    except ValueError as exc:
        assert "provider" in str(exc)
    else:
        raise AssertionError("ambiguous provider should be rejected")


def test_packaged_cli_installs_pi_profile(tmp_path, capsys):
    node = tmp_path / "node.exe"
    pi_bundle = tmp_path / "cli.js"
    node.write_bytes(b"node")
    pi_bundle.write_bytes(b"pi")

    assert (
        cli.main(
            [
                "agent-profile",
                "pi",
                "install",
                "--profile-dir",
                str(tmp_path / "profile"),
                "--session-dir",
                str(tmp_path / "sessions"),
                "--launcher",
                str(tmp_path / "pi-eda.cmd"),
                "--node",
                str(node),
                "--pi-cli",
                str(pi_bundle),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)

    assert result["status"] == "installed"
    assert result["agent"] == "pi"
    assert result["runtime_tools"] == 11
    assert Path(result["runtime_extension"]).is_dir()
