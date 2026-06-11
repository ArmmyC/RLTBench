from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable


def pass_at_k(n: int, c: int, k: int) -> float:
    if not 1 <= k <= n:
        raise ValueError("k must be between 1 and n")
    if not 0 <= c <= n:
        raise ValueError("c must be between 0 and n")
    if n - c < k:
        return 1.0
    return 1.0 - (math.comb(n - c, k) / math.comb(n, k))


def aggregate_results(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    samples = list(rows)
    total = len(samples)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        by_task[str(row["task_id"])].append(row)

    pass_k: dict[str, float] = {}
    if by_task:
        min_samples = min(len(group) for group in by_task.values())
        for k in range(1, min_samples + 1):
            values = [
                pass_at_k(len(group), sum(bool(item["final_pass"]) for item in group), k)
                for group in by_task.values()
            ]
            pass_k[f"pass@{k}"] = sum(values) / len(values)

    return {
        "samples": total,
        "tasks": len(by_task),
        "syntax_pass_rate": _rate(samples, "compile_pass"),
        "functional_pass_rate": _rate(samples, "final_pass"),
        "pass_at_k": pass_k,
        "failure_categories": dict(Counter(str(row["failure_category"]) for row in samples)),
    }


def _rate(rows: list[dict[str, Any]], field: str) -> float:
    return sum(bool(row[field]) for row in rows) / len(rows) if rows else 0.0

