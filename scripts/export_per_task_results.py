from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rtlbench.per_task import export_per_task_results, render_per_task_csv, render_per_task_jsonl
from rtlbench.registry import RegistryError, load_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export sanitized per-task benchmark results")
    parser.add_argument("--registry", default="runs/index.yaml")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output-dir", default="artifacts/baseline_v0.2")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        baseline = load_registry(args.registry, args.baseline, strict=args.strict)
        data = export_per_task_results(baseline, strict=args.strict)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = output_dir / "per_task_results.jsonl"
        csv_path = output_dir / "per_task_results.csv"
        jsonl_path.write_text(render_per_task_jsonl(data["rows"]), encoding="utf-8", newline="")
        csv_path.write_text(render_per_task_csv(data["rows"]), encoding="utf-8", newline="")
        print(f"Generated {jsonl_path} ({len(data['rows'])} rows)")
        print(f"Generated {csv_path} ({len(data['warnings'])} warnings)")
        for warning in data["warnings"]:
            print(f"WARNING: {warning}", file=sys.stderr)
        return 0
    except (RegistryError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
