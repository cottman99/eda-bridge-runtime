import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_chart_data_and_bilingual_readmes_stay_aligned() -> None:
    data = json.loads((ROOT / "evals" / "public-readme-data-v1.json").read_text(encoding="utf-8"))
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert data["schema"] == "eda.public-readme-data/v1"
    for relative_path in (
        "docs/assets/readme/runtime-complete-workflow-time.png",
        "docs/assets/readme/codex-pi-bounded-tests.png",
        "docs/assets/readme/supervised-live-edit-latency.png",
    ):
        assert (ROOT / relative_path).is_file()
        assert relative_path in english
        assert relative_path in chinese

    for value in ("40.594", "36.953", "5.157", "93–187", "296–453"):
        assert value in english
        assert value in chinese


def test_public_chart_generator_is_tracked_and_source_backed() -> None:
    generator = ROOT / "scripts" / "render_public_readme_charts.py"
    data_path = ROOT / "evals" / "public-readme-data-v1.json"
    assert generator.is_file()
    assert data_path.is_file()
    assert "public-readme-data-v1.json" in generator.read_text(encoding="utf-8")
