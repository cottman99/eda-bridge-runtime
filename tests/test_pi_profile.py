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
