from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_reports(output_dir: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    with (output_dir / "results.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key in ("samples", "tasks", "syntax_pass_rate", "functional_pass_rate"):
            writer.writerow([key, summary[key]])
        for key, value in summary["pass_at_k"].items():
            writer.writerow([key, value])
        for key, value in summary["failure_categories"].items():
            writer.writerow([f"failure:{key}", value])

