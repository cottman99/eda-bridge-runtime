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


def test_matrix_can_select_exact_cases_without_replaying_lower_levels(tmp_path):
    matrix = load_matrix()
    write_case(tmp_path, "l0.safe", 0, "forbidden")
    write_case(tmp_path, "l2.target", 2, "forbidden")

    selected, skipped = matrix.load_cases(
        tmp_path,
        max_level=0,
        approve_mutations=False,
        case_ids={"l2.target"},
    )

    assert [case["case_id"] for case in selected] == ["l2.target"]
    assert skipped == []


def test_matrix_result_paths_preserve_single_run_names_and_separate_trials(tmp_path):
    matrix = load_matrix()

    assert (
        matrix.result_path(
            tmp_path, case_id="l0.connections", agent="codex", trial=1, repetitions=1
        ).name
        == "l0_connections__codex.json"
    )
    assert (
        matrix.result_path(
            tmp_path, case_id="l0.connections", agent="codex", trial=2, repetitions=3
        ).name
        == "l0_connections__codex__trial_02.json"
    )


def test_matrix_preflights_required_variables_without_starting_agents():
    matrix = load_matrix()
    cases = [
        {"variables": ["ADS_CONNECTION"]},
        {"variables": ["ANSYS_CONNECTION", "ADS_CONNECTION"]},
    ]

    supplied = matrix.supplied_variable_names(["ADS_CONNECTION=ads-display4"])

    assert matrix.missing_case_variables(cases, supplied) == ["ANSYS_CONNECTION"]
