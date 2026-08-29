import importlib.util
import json
from pathlib import Path


def load_matrix():
    path = Path(__file__).parents[1] / "evals" / "run_matrix.py"
    spec = importlib.util.spec_from_file_location("eval_matrix", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_case(root: Path, case_id: str, level: int, mutation: str) -> None:
    (root / f"{case_id}.json").write_text(
        json.dumps({"case_id": case_id, "level": level, "safety": {"mutation": mutation}}),
        encoding="utf-8",
    )


def test_matrix_selects_by_level_and_requires_explicit_mutation_approval(tmp_path):
    matrix = load_matrix()
    write_case(tmp_path, "l0.safe", 0, "forbidden")
    write_case(tmp_path, "l3.mutation", 3, "disposable-only")
    write_case(tmp_path, "l5.later", 5, "forbidden")

    selected, skipped = matrix.load_cases(tmp_path, max_level=4, approve_mutations=False)

    assert [case["case_id"] for case in selected] == ["l0.safe"]
    assert skipped == [{"case_id": "l3.mutation", "reason": "mutation_not_approved"}]
