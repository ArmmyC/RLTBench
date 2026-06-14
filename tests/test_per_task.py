import json
from pathlib import Path

from rtlbench.per_task import SANITIZED_FIELDS, export_per_task_results, render_per_task_csv, render_per_task_jsonl
from rtlbench.registry import load_registry
from test_registry import run_record, write_registry


def test_sanitized_export_whitelists_fields_and_token_usage(tmp_path: Path) -> None:
    results = tmp_path / "results.jsonl"
    results.write_text(json.dumps({
        "task_id": "task-a", "sample_id": 2, "compile_pass": True, "sim_pass": False,
        "final_pass": False, "failure_category": "simulation_failure", "prompt_hash": "abc",
        "latency_seconds": 1.25, "token_usage": {"completion_tokens": 12, "total_tokens": 20},
        "raw_response": "SECRET RESPONSE", "extracted_rtl": "module leaked; endmodule",
        "error_log": "PRIVATE LOG", "prompt": "FULL PROMPT", "api_key": "secret",
    }) + "\n", encoding="utf-8")
    baseline = load_registry(write_registry(tmp_path, [run_record(results_path=str(results))]), "baseline_v0_1")
    data = export_per_task_results(baseline)
    assert tuple(data["rows"][0]) == SANITIZED_FIELDS
    assert data["rows"][0]["completion_tokens"] == 12
    output = render_per_task_jsonl(data["rows"]) + render_per_task_csv(data["rows"])
    for forbidden in ("SECRET RESPONSE", "module leaked", "PRIVATE LOG", "FULL PROMPT", "secret"):
        assert forbidden not in output


def test_sanitized_export_warns_for_missing_results(tmp_path: Path) -> None:
    baseline = load_registry(write_registry(tmp_path, [run_record(results_path="missing/results.jsonl")]), "baseline_v0_1")
    data = export_per_task_results(baseline)
    assert data["rows"] == []
    assert "unavailable" in data["warnings"][0]
    assert render_per_task_jsonl([]) == ""
    assert render_per_task_csv([]).startswith("baseline,benchmark,mode")
