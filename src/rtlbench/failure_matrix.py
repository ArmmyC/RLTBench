from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rtlbench.per_task import load_per_task_artifact, sanitize_record
from rtlbench.registry import LoadedBaseline, resolve_registered_path


FIELDS = (
    "baseline", "benchmark", "mode", "task_id", "model", "sample_id",
    "final_pass", "compile_pass", "sim_pass", "failure_category", "source_results_path",
)


def _matrix_row(row: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "baseline": row["baseline"], "benchmark": row["benchmark"], "mode": row["mode"],
        "task_id": row["task_id"], "model": row["model"], "sample_id": row["sample_id"],
        "final_pass": bool(row["final_pass"]), "compile_pass": bool(row["compile_pass"]),
        "sim_pass": bool(row["sim_pass"]), "failure_category": row["failure_category"],
        "source_results_path": source,
    }


def _read_live_rows(baseline: LoadedBaseline, run: Any, path: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    rows, warnings = [], []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("row is not an object")
                rows.append(_matrix_row(sanitize_record(baseline, run, record), str(path)))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                message = f"{run.registration['id']}:{line_number}: malformed JSON skipped"
                if strict:
                    raise ValueError(message) from exc
                warnings.append(message)
    return rows, warnings


def build_failure_matrix(
    baseline: LoadedBaseline, *, benchmark: str | None = None, mode: str | None = None,
    strict: bool = False, per_task_artifacts: str | Path | None = None,
    prefer_artifacts: bool = False, report_version: str = "v0.1",
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    coverage: list[dict[str, Any]] = []
    summary_model: dict[str, Counter[str]] = defaultdict(Counter)
    summary_benchmark: dict[str, Counter[str]] = defaultdict(Counter)
    artifact_rows, artifact_warnings = (load_per_task_artifact(per_task_artifacts, strict=strict) if per_task_artifacts else ([], []))
    warnings.extend(artifact_warnings)
    artifacts_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in artifact_rows:
        if row["baseline"] == baseline.key:
            artifacts_by_run[str(row["source_run_id"])].append(row)

    for run in baseline.runs:
        registration = run.registration
        if benchmark and registration["benchmark"] != benchmark:
            continue
        if mode and registration["mode"] != mode:
            continue
        summary_model[registration["model"]].update(run.summary.get("failure_categories", {}))
        summary_benchmark[registration["benchmark"]].update(run.summary.get("failure_categories", {}))
        live_path = resolve_registered_path(run, "results_path", baseline.repo_root)
        live_available = bool(live_path and live_path.is_file())
        sanitized = artifacts_by_run.get(registration["id"], [])
        selected_rows: list[dict[str, Any]] = []
        source = "summary_only"
        if live_available and not prefer_artifacts:
            selected_rows, live_warnings = _read_live_rows(baseline, run, live_path, strict)
            warnings.extend(live_warnings)
            source = "live_results"
        elif sanitized:
            selected_rows = [_matrix_row(row, str(per_task_artifacts)) for row in sanitized]
            source = "sanitized_artifact"
        elif live_available:
            selected_rows, live_warnings = _read_live_rows(baseline, run, live_path, strict)
            warnings.extend(live_warnings)
            source = "live_results"
        else:
            warnings.append(f"{registration['id']}: per-task results unavailable; using summary fallback")
        rows.extend(selected_rows)
        coverage.append({
            "run_id": registration["id"], "benchmark": registration["benchmark"],
            "mode": registration["mode"], "model": registration["model"],
            "available": bool(selected_rows), "rows": len(selected_rows), "source": source,
        })

    rows.sort(key=lambda row: (row["benchmark"], row["mode"], row["task_id"], row["model"], row["sample_id"]))
    per_task_model: dict[str, Counter[str]] = defaultdict(Counter)
    per_task_benchmark: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        per_task_model[row["model"]][row["failure_category"]] += 1
        per_task_benchmark[row["benchmark"]][row["failure_category"]] += 1
    for model, counts in per_task_model.items():
        if not summary_model[model]:
            summary_model[model].update(counts)
    for name, counts in per_task_benchmark.items():
        if not summary_benchmark[name]:
            summary_benchmark[name].update(counts)
    data = {
        "baseline": baseline.key, "report_version": report_version,
        "models": list(baseline.metadata["models"]), "rows": rows, "coverage": coverage,
        "summary_failure_categories": {model: dict(counts) for model, counts in summary_model.items()},
        "benchmark_failure_categories": {name: dict(counts) for name, counts in summary_benchmark.items()},
        "warnings": warnings,
    }
    data["analysis"] = analyze_tasks(data)
    return data


def _task_outcomes(data: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, bool]]:
    grouped: dict[tuple[str, str, str, str], list[bool]] = defaultdict(list)
    for row in data["rows"]:
        grouped[(row["benchmark"], row["mode"], row["task_id"], row["model"])].append(row["final_pass"])
    outcomes: dict[tuple[str, str, str], dict[str, bool]] = defaultdict(dict)
    for (benchmark, mode, task_id, model), values in grouped.items():
        outcomes[(benchmark, mode, task_id)][model] = any(values)
    return outcomes


def analyze_tasks(data: dict[str, Any]) -> dict[str, Any]:
    outcomes = _task_outcomes(data)
    failed_all, solved_all, hardest = [], [], []
    unique: dict[str, list[str]] = defaultdict(list)
    for key, model_values in sorted(outcomes.items()):
        if len(model_values) < 2:
            continue
        passed = sorted(model for model, result in model_values.items() if result)
        label = "/".join(key)
        failed = len(model_values) - len(passed)
        hardest.append({"task": label, "failed_models": failed, "models_compared": len(model_values)})
        if not passed:
            failed_all.append(label)
        if len(passed) == len(model_values):
            solved_all.append(label)
        if len(passed) == 1:
            unique[passed[0]].append(label)
    hardest.sort(key=lambda item: (-item["failed_models"], item["task"]))
    pass1: dict[tuple[str, str], bool] = {}
    pass5: dict[tuple[str, str], bool] = {}
    for (benchmark, mode, task_id), model_values in outcomes.items():
        if benchmark != "verilogeval" or mode not in {"pass1", "pass5"}:
            continue
        target = pass1 if mode == "pass1" else pass5
        target.update({(task_id, model): passed for model, passed in model_values.items()})
    recovered = [f"{task}: {model}" for (task, model), passed in sorted(pass5.items()) if passed and not pass1.get((task, model), False)]
    return {
        "failed_all": failed_all, "solved_all": solved_all, "unique_by_model": dict(unique),
        "pass5_recovered": recovered, "hardest_tasks": hardest,
    }


def _list_section(lines: list[str], title: str, values: list[str], empty: str = "None detected in available data.") -> None:
    lines.extend(["", f"## {title}", ""])
    lines.extend([f"- {value}" for value in values] or [empty])


def render_failure_markdown(data: dict[str, Any]) -> str:
    version = data.get("report_version", "v0.1")
    lines = [f"# Baseline {version} Cross-Model Failure Matrix", "", "## Coverage Summary", "",
             "| Benchmark | Mode | Model | Run | Source | Rows |", "|---|---|---|---|---|---:|"]
    for item in data["coverage"]:
        lines.append(f"| {item['benchmark']} | {item['mode']} | {item['model']} | {item['run_id']} | {item['source']} | {item['rows']} |")
    summary = data["summary_failure_categories"]
    categories = sorted({category for counts in summary.values() for category in counts})
    lines.extend(["", "## Failure Category Counts by Model", ""])
    if categories:
        lines += ["| Model | " + " | ".join(categories) + " |", "|---|" + "---:|" * len(categories)]
        for model in data["models"]:
            lines.append(f"| {model} | " + " | ".join(str(summary.get(model, {}).get(category, 0)) for category in categories) + " |")
    benchmark_counts = data["benchmark_failure_categories"]
    lines.extend(["", "## Failure Category Counts by Benchmark", ""])
    if categories:
        lines += ["| Benchmark | " + " | ".join(categories) + " |", "|---|" + "---:|" * len(categories)]
        for name in sorted(benchmark_counts):
            lines.append(f"| {name} | " + " | ".join(str(benchmark_counts[name].get(category, 0)) for category in categories) + " |")
    if not data["rows"]:
        lines.extend(["", "## Per-Task Analysis", "", "Per-task failure data is not available for this run. The summary-level baseline is still shown from registered summaries."])
        for title in ("Tasks Failed by All Available Models", "Tasks Solved by All Available Models", "Tasks Uniquely Solved by One Model", "Tasks Recovered by Pass@5", "Hardest Tasks"):
            _list_section(lines, title, [], "Unavailable without per-task results.")
    else:
        analysis = data["analysis"]
        _list_section(lines, "Tasks Failed by All Available Models", analysis["failed_all"])
        _list_section(lines, "Tasks Solved by All Available Models", analysis["solved_all"])
        unique_values = [f"{task}: {model}" for model, tasks in sorted(analysis["unique_by_model"].items()) for task in tasks]
        _list_section(lines, "Tasks Uniquely Solved by One Model", unique_values)
        _list_section(lines, "Tasks Recovered by Pass@5", analysis["pass5_recovered"], "No pass@1/pass@5 recovery detected.")
        hardest = [f"{item['task']}: {item['failed_models']}/{item['models_compared']} models failed" for item in analysis["hardest_tasks"]]
        _list_section(lines, "Hardest Tasks", hardest)
    _list_section(lines, "Missing Data Warnings", data["warnings"], "None.")
    return "\n".join(lines) + "\n"


def render_failure_csv(data: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(data["rows"])
    return output.getvalue()
