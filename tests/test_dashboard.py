from pathlib import Path

from rtlbench.comparison import build_comparison
from rtlbench.dashboard import render_dashboard
from rtlbench.failure_matrix import build_failure_matrix
from rtlbench.registry import load_registry
from test_registry import run_record, write_registry
import json


def test_dashboard_html_contains_required_sections_and_no_secrets(tmp_path: Path) -> None:
    runs = [
        run_record(id="ve", benchmark="verilogeval", mode="pass1", manual_summary={"functional_pass_rate": 0.5}),
        run_record(id="ve5", benchmark="verilogeval", mode="pass5", samples_per_task=5, temperature=0.6, manual_summary={"pass_at_k": {"pass@5": 0.7}}),
        run_record(id="rt", benchmark="rtllm2", mode="pass1", max_tokens=4096, manual_summary={"functional_pass_rate": 0.4}),
        run_record(id="equiv", benchmark="rtlopt", mode="equivalence", evaluation_kind="equivalence", max_tokens=4096, evaluator_type="yosys_equivalence", manual_summary={"functional_pass_rate": 0.6}, rtlopt_metrics={"equivalence_pass_rate": 0.6}),
    ]
    baseline = load_registry(write_registry(tmp_path, runs, benchmarks=["verilogeval", "rtllm2", "rtlopt"]), "baseline_v0_1")
    output = render_dashboard(build_comparison(baseline), build_failure_matrix(baseline))
    assert "RTLBench Baseline v0.1" in output
    assert "model-a" in output
    assert "Functional RTL Generation" in output
    assert "RTL-OPT Behavior-Preserving Optimization" in output
    assert "Per-task failure data is not available" in output
    assert "api_key" not in output.lower()


def test_dashboard_renders_per_task_analysis(tmp_path: Path) -> None:
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    a.write_text(json.dumps({"task_id": "hard", "sample_id": 0, "final_pass": False, "compile_pass": False, "sim_pass": False, "failure_category": "compile_failure"}) + "\n", encoding="utf-8")
    b.write_text(json.dumps({"task_id": "hard", "sample_id": 0, "final_pass": False, "compile_pass": True, "sim_pass": False, "failure_category": "simulation_failure"}) + "\n", encoding="utf-8")
    runs = [run_record(id="a", model="model-a", results_path=str(a)), run_record(id="b", model="model-b", served_model_name="served-b", results_path=str(b))]
    baseline = load_registry(write_registry(tmp_path, runs, models=["model-a", "model-b"]), "baseline_v0_1")
    output = render_dashboard(build_comparison(baseline), build_failure_matrix(baseline))
    assert "Per-task coverage" in output
    assert "Failed by all models" in output
    assert "verilogeval/pass1/hard" in output
