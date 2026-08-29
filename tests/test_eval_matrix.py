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


def write_case(
    root: Path, case_id: str, level: int, mutation: str, solve: str = "forbidden"
) -> None:
    (root / f"{case_id}.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "level": level,
                "safety": {"mutation": mutation, "solve": solve},
            }
        ),
        encoding="utf-8",
    )


def test_matrix_selects_by_level_and_requires_explicit_mutation_approval(tmp_path):
    matrix = load_matrix()
    write_case(tmp_path, "l0.safe", 0, "forbidden")
    write_case(tmp_path, "l3.mutation", 3, "disposable-only")
    write_case(tmp_path, "l5.later", 5, "forbidden")

    selected, skipped = matrix.load_cases(
        tmp_path, max_level=4, approve_mutations=False, approve_solves=False
    )

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
        approve_solves=False,
        case_ids={"l2.target"},
    )

    assert [case["case_id"] for case in selected] == ["l2.target"]
    assert skipped == []


def test_matrix_requires_separate_explicit_solve_approval(tmp_path):
    matrix = load_matrix()
    write_case(
        tmp_path,
        "l6.solve",
        6,
        "disposable-only",
        solve="one-generated-input-only",
    )

    selected, skipped = matrix.load_cases(
        tmp_path,
        max_level=6,
        approve_mutations=True,
        approve_solves=False,
    )

    assert selected == []
    assert skipped == [{"case_id": "l6.solve", "reason": "solve_not_approved"}]

    selected, skipped = matrix.load_cases(
        tmp_path,
        max_level=6,
        approve_mutations=True,
        approve_solves=True,
    )

    assert [case["case_id"] for case in selected] == ["l6.solve"]
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


def test_matrix_expands_owned_run_placeholders_without_interpreting_other_braces():
    matrix = load_matrix()

    assert matrix.expand_run_variables(
        [
            "ROOT=/scratch/{agent}/trial-{trial}",
            "KEY=run-{sequence}",
            'JSON={"literal":true}',
        ],
        agent="pi",
        trial=3,
        sequence=6,
    ) == [
        "ROOT=/scratch/pi/trial-3",
        "KEY=run-6",
        'JSON={"literal":true}',
    ]


def test_empty_or_all_skipped_matrix_is_not_reported_as_success():
    matrix = load_matrix()

    assert matrix.matrix_exit_code([]) == 2
    assert matrix.matrix_exit_code([{"passed": True}]) == 0
    assert matrix.matrix_exit_code([{"passed": False}]) == 1


def test_matrix_interleaves_agents_and_rotates_first_client_by_trial_and_case():
    matrix = load_matrix()
    cases = [{"case_id": "l0.one"}, {"case_id": "l1.two"}]

    schedule = matrix.execution_schedule(cases, ["codex", "pi"], repetitions=2)

    assert [(case["case_id"], trial, agent) for case, trial, agent in schedule] == [
        ("l0.one", 1, "codex"),
        ("l0.one", 1, "pi"),
        ("l0.one", 2, "pi"),
        ("l0.one", 2, "codex"),
        ("l1.two", 1, "pi"),
        ("l1.two", 1, "codex"),
        ("l1.two", 2, "codex"),
        ("l1.two", 2, "pi"),
    ]
