from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from rtlbench.comparison import build_comparison, render_json
from rtlbench.dashboard import render_dashboard
from rtlbench.failure_matrix import build_failure_matrix, render_failure_csv
from rtlbench.registry import RegistryError, load_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Baseline v0.1 static dashboard")
    parser.add_argument("--registry", default="runs/index.yaml")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--comparison-json", default="reports/baseline_v0.1_public_rtl_benchmarks.json")
    parser.add_argument("--failure-csv", default="reports/baseline_v0.1_failure_matrix.csv")
    parser.add_argument("--per-task-artifacts", default="artifacts/baseline_v0.2/per_task_results.jsonl")
    parser.add_argument("--prefer-artifacts", action="store_true")
    parser.add_argument("--output", default="dashboard/index.html")
    args = parser.parse_args(argv)
    try:
        baseline = load_registry(args.registry, args.baseline)
        comparison_path = Path(args.comparison_json)
        comparison = json.loads(comparison_path.read_text(encoding="utf-8")) if comparison_path.is_file() else build_comparison(baseline)
        artifact_path = Path(args.per_task_artifacts)
        failure = build_failure_matrix(
            baseline,
            per_task_artifacts=artifact_path if artifact_path.is_file() else None,
            prefer_artifacts=args.prefer_artifacts,
            report_version="v0.2" if artifact_path.is_file() else "v0.1",
        )
        failure_path = Path(args.failure_csv)
        if failure_path.is_file() and not failure["rows"]:
            with failure_path.open(newline="", encoding="utf-8") as handle:
                failure["rows"] = [
                    {
                        **row,
                        "sample_id": int(row["sample_id"]),
                        "final_pass": row["final_pass"].lower() == "true",
                        "compile_pass": row["compile_pass"].lower() == "true",
                        "sim_pass": row["sim_pass"].lower() == "true",
                    }
                    for row in csv.DictReader(handle)
                ]
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_dashboard(comparison, failure), encoding="utf-8", newline="")
        data_dir = output.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "baseline_v0.1.json").write_text(render_json(build_comparison(baseline)), encoding="utf-8", newline="")
        (data_dir / "failure_matrix.csv").write_text(render_failure_csv(failure), encoding="utf-8", newline="")
        print(f"Generated {output}")
        print(f"Generated {data_dir / 'baseline_v0.1.json'}")
        print(f"Generated {data_dir / 'failure_matrix.csv'}")
        return 0
    except (RegistryError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
