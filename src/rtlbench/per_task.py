from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from rtlbench.registry import LoadedBaseline, LoadedRun, resolve_registered_path


SANITIZED_FIELDS = (
    "baseline",
    "benchmark",
    "mode",
    "model",
    "served_model_name",
    "task_id",
    "sample_id",
    "compile_pass",
    "sim_pass",
    "final_pass",
    "failure_category",
    "prompt_hash",
    "latency_seconds",
    "completion_tokens",
    "total_tokens",
    "source_run_id",
)


def _token_value(record: dict[str, Any], key: str) -> int | None:
    usage = record.get("token_usage") or record.get("usage") or {}
    value = usage.get(key) if isinstance(usage, dict) else None
    if value is None:
        value = record.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def sanitize_record(baseline: LoadedBaseline, run: LoadedRun, record: dict[str, Any]) -> dict[str, Any]:
    registration = run.registration
    return {
        "baseline": baseline.key,
        "benchmark": registration["benchmark"],
        "mode": registration["mode"],
        "model": registration["model"],
        "served_model_name": registration["served_model_name"],
        "task_id": str(record.get("task_id", "unknown")),
        "sample_id": int(record.get("sample_id", 0)),
        "compile_pass": bool(record.get("compile_pass", False)),
        "sim_pass": bool(record.get("sim_pass", False)),
        "final_pass": bool(record.get("final_pass", False)),
        "failure_category": str(record.get("failure_category", "unknown")),
        "prompt_hash": str(record.get("prompt_hash", "")),
        "latency_seconds": record.get("latency_seconds") if isinstance(record.get("latency_seconds"), (int, float)) else None,
        "completion_tokens": _token_value(record, "completion_tokens"),
        "total_tokens": _token_value(record, "total_tokens"),
        "source_run_id": registration["id"],
    }


def export_per_task_results(baseline: LoadedBaseline, *, strict: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    coverage: list[dict[str, Any]] = []
    for run in baseline.runs:
        path = resolve_registered_path(run, "results_path", baseline.repo_root)
        if not path or not path.is_file():
            warnings.append(f"{run.registration['id']}: results.jsonl unavailable; no sanitized rows exported")
            coverage.append({"run_id": run.registration["id"], "available": False, "rows": 0})
            continue
        count = 0
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("row is not an object")
                    rows.append(sanitize_record(baseline, run, record))
                    count += 1
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    message = f"{run.registration['id']}:{line_number}: malformed result skipped"
                    if strict:
                        raise ValueError(message) from exc
                    warnings.append(message)
        coverage.append({"run_id": run.registration["id"], "available": True, "rows": count})
    rows.sort(key=lambda row: (row["benchmark"], row["mode"], row["task_id"], row["model"], row["sample_id"]))
    return {"rows": rows, "warnings": warnings, "coverage": coverage}


def render_per_task_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps({field: row.get(field) for field in SANITIZED_FIELDS}, sort_keys=False) + "\n" for row in rows)


def render_per_task_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=SANITIZED_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def load_per_task_artifact(path: str | Path, *, strict: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    artifact = Path(path)
    if not artifact.is_file():
        return [], [f"Sanitized per-task artifact unavailable at {artifact}"]
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    with artifact.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict) or any(field not in record for field in SANITIZED_FIELDS):
                    raise ValueError("missing sanitized field")
                rows.append({field: record[field] for field in SANITIZED_FIELDS})
            except (json.JSONDecodeError, ValueError) as exc:
                message = f"{artifact}:{line_number}: malformed sanitized row skipped"
                if strict:
                    raise ValueError(message) from exc
                warnings.append(message)
    return rows, warnings
