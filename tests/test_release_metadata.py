import json
from pathlib import Path

import eda_bridge_runtime


def test_plugin_and_python_package_versions_match():
    root = Path(__file__).parents[1]
    manifest = json.loads(
        (root / "plugins/eda-bridge-runtime/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    )

    plugin_version = manifest["version"].replace("-alpha.", "a")

    assert plugin_version == eda_bridge_runtime.__version__
