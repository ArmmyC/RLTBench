import pytest

from rtlbench.metrics import aggregate_results, pass_at_k


def test_pass_at_k() -> None:
    assert pass_at_k(10, 2, 1) == pytest.approx(0.2)
    assert pass_at_k(5, 1, 5) == 1.0


def test_aggregation() -> None:
    rows = [
        {"task_id": "a", "compile_pass": True, "final_pass": True, "failure_category": "passed"},
        {"task_id": "a", "compile_pass": True, "final_pass": False, "failure_category": "simulation_failure"},
        {"task_id": "b", "compile_pass": False, "final_pass": False, "failure_category": "compile_failure"},
        {"task_id": "b", "compile_pass": True, "final_pass": True, "failure_category": "passed"},
    ]
    summary = aggregate_results(rows)
    assert summary["syntax_pass_rate"] == 0.75
    assert summary["functional_pass_rate"] == 0.5
    assert summary["pass_at_k"]["pass@1"] == 0.5
    assert summary["pass_at_k"]["pass@2"] == 1.0

