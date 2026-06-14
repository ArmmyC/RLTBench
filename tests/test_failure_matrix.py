import json
from pathlib import Path

from rtlbench.failure_matrix import build_failure_matrix, render_failure_csv, render_failure_markdown
from rtlbench.registry import load_registry
from rtlbench.per_task import render_per_task_jsonl
from test_registry import run_record, write_registry


def write_results(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_failure_matrix_detects_shared_and_unique_outcomes(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    write_results(a, [
        {"task_id": "all_pass", "sample_id": 0, "final_pass": True, "compile_pass": True, "sim_pass": True, "failure_category": "passed"},
        {"task_id": "all_fail", "sample_id": 0, "final_pass": False, "compile_pass": False, "sim_pass": False, "failure_category": "compile_failure"},
        {"task_id": "unique", "sample_id": 0, "final_pass": True, "compile_pass": True, "sim_pass": True, "failure_category": "passed"},
    ])
    write_results(b, [
        {"task_id": "all_pass", "sample_id": 0, "final_pass": True, "compile_pass": True, "sim_pass": True, "failure_category": "passed"},
        {"task_id": "all_fail", "sample_id": 0, "final_pass": False, "compile_pass": True, "sim_pass": False, "failure_category": "simulation_failure"},
        {"task_id": "unique", "sample_id": 0, "final_pass": False, "compile_pass": True, "sim_pass": False, "failure_category": "simulation_failure"},
    ])
    runs = [run_record(id="a", model="model-a", results_path=str(a)), run_record(id="b", model="model-b", served_model_name="served-b", results_path=str(b))]
    registry = write_registry(tmp_path, runs, models=["model-a", "model-b"])
    data = build_failure_matrix(load_registry(registry, "baseline_v0_1"))
    markdown = render_failure_markdown(data)
    assert "all_fail" in markdown
    assert "all_pass" in markdown
    assert "unique: model-a" in markdown
    assert "compile_failure" in markdown
    assert len(render_failure_csv(data).splitlines()) == 7


def test_missing_results_warns_without_crashing(tmp_path: Path) -> None:
    run = run_record(results_path="missing/results.jsonl")
    data = build_failure_matrix(load_registry(write_registry(tmp_path, [run]), "baseline_v0_1"))
    assert not data["rows"]
    assert "unavailable" in data["warnings"][0]
    assert "Per-task failure data is not available" in render_failure_markdown(data)


def test_artifact_fallback_live_precedence_and_pass5_recovery(tmp_path: Path) -> None:
    live = tmp_path / "live.jsonl"
    write_results(live, [{"task_id": "recovered", "sample_id": 0, "final_pass": False, "compile_pass": True, "sim_pass": False, "failure_category": "simulation_failure"}])
    runs = [
        run_record(id="a1", model="model-a", mode="pass1", results_path=str(live)),
        run_record(id="a5", model="model-a", mode="pass5", samples_per_task=5, temperature=0.6, results_path="missing-a5.jsonl"),
        run_record(id="b1", model="model-b", served_model_name="served-b", mode="pass1", results_path="missing-b1.jsonl"),
        run_record(id="b5", model="model-b", served_model_name="served-b", mode="pass5", samples_per_task=5, temperature=0.6, results_path="missing-b5.jsonl"),
    ]
    baseline = load_registry(write_registry(tmp_path, runs, models=["model-a", "model-b"]), "baseline_v0_1")
    artifact_rows = [
        {"baseline": "baseline_v0_1", "benchmark": "verilogeval", "mode": mode, "model": model,
         "served_model_name": f"served-{model[-1]}", "task_id": task, "sample_id": 0,
         "compile_pass": passed, "sim_pass": passed, "final_pass": passed,
         "failure_category": "passed" if passed else "compile_failure", "prompt_hash": "hash",
         "latency_seconds": 1.0, "completion_tokens": 10, "total_tokens": 15, "source_run_id": run_id}
        for run_id, mode, model, task, passed in (
            ("a1", "pass1", "model-a", "recovered", True),
            ("a5", "pass5", "model-a", "recovered", True),
            ("b1", "pass1", "model-b", "recovered", False),
            ("b5", "pass5", "model-b", "recovered", True),
        )
    ]
    artifact = tmp_path / "sanitized.jsonl"
    artifact.write_text(render_per_task_jsonl(artifact_rows), encoding="utf-8")
    data = build_failure_matrix(baseline, per_task_artifacts=artifact)
    assert next(row for row in data["rows"] if row["model"] == "model-a" and row["mode"] == "pass1")["final_pass"] is False
    assert "recovered: model-b" in data["analysis"]["pass5_recovered"]
    assert any(item["source"] == "sanitized_artifact" for item in data["coverage"])
    preferred = build_failure_matrix(baseline, per_task_artifacts=artifact, prefer_artifacts=True)
    assert next(row for row in preferred["rows"] if row["model"] == "model-a" and row["mode"] == "pass1")["final_pass"] is True
