from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rtlbench.failure_matrix import build_failure_matrix, render_failure_csv, render_failure_markdown
from rtlbench.registry import RegistryError, load_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate cross-model failure analysis")
    parser.add_argument("--registry", default="runs/index.yaml")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output-md", default="reports/baseline_v0.1_failure_matrix.md")
    parser.add_argument("--output-csv", default="reports/baseline_v0.1_failure_matrix.csv")
    parser.add_argument("--benchmark")
    parser.add_argument("--mode")
    parser.add_argument("--per-task-artifacts")
    parser.add_argument("--prefer-artifacts", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        baseline = load_registry(args.registry, args.baseline, strict=args.strict)
        report_version = "v0.2" if "v0.2" in args.output_md else "v0.1"
        data = build_failure_matrix(
            baseline, benchmark=args.benchmark, mode=args.mode, strict=args.strict,
            per_task_artifacts=args.per_task_artifacts, prefer_artifacts=args.prefer_artifacts,
            report_version=report_version,
        )
        outputs = ((Path(args.output_md), render_failure_markdown(data)), (Path(args.output_csv), render_failure_csv(data)))
        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
            print(f"Generated {path}")
        print(f"Warnings: {len(data['warnings'])}")
        return 0
    except (RegistryError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
