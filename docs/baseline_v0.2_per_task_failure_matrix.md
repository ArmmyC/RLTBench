# Baseline v0.2 Per-Task Failure Matrix

Baseline v0.2 extends the frozen Baseline v0.1 registry with small sanitized per-task artifacts. It does not add model runs, alter benchmark settings, or replace the v0.1 reports.

## Data Flow

`scripts/export_per_task_results.py` reads only registered, accessible `results.jsonl` files. Each source row is reduced to this allowlist:

```text
baseline, benchmark, mode, model, served_model_name, task_id, sample_id,
compile_pass, sim_pass, final_pass, failure_category, prompt_hash,
latency_seconds, completion_tokens, total_tokens, source_run_id
```

The exporter excludes raw responses, extracted RTL, prompts, error-log contents, API credentials, secrets, model weights, caches, and large logs. JSONL and CSV rows are sorted deterministically.

## Source Precedence

For every registered run, failure analysis selects exactly one per-task source:

1. Accessible live `results.jsonl`.
2. Matching rows in the sanitized JSONL artifact.
3. Registered summary fallback, with no fabricated task rows.

Use `--prefer-artifacts` when the committed sanitized snapshot should override an accessible live file. Coverage tables identify each run as `live_results`, `sanitized_artifact`, or `summary_only`.

## Generate

```bash
python scripts/export_per_task_results.py --registry runs/index.yaml --baseline baseline_v0_1 --output-dir artifacts/baseline_v0.2
python scripts/analyze_cross_model_failures.py --registry runs/index.yaml --baseline baseline_v0_1 --per-task-artifacts artifacts/baseline_v0.2/per_task_results.jsonl --output-md reports/baseline_v0.2_failure_matrix.md --output-csv reports/baseline_v0.2_failure_matrix.csv
python scripts/build_dashboard.py --registry runs/index.yaml --baseline baseline_v0_1
python -m pytest
```

## Analysis Produced

When per-task rows are available, the report and dashboard show tasks failed by all compared models, solved by all compared models, uniquely solved by one model, recovered by VerilogEval pass@5, hardest tasks by failed-model count, and coverage by benchmark, mode, and model. Failure-category totals are reported by model and benchmark from registered summaries so they remain available in portable checkouts.

## Portable Checkout Behavior

Historical raw outputs are intentionally gitignored. If none of the registered `results.jsonl` files are available, export succeeds with an empty JSONL file and a header-only CSV, while emitting warnings for every unavailable run. The v0.2 report then retains summary-level counts and explicitly marks per-task sections unavailable. Run the exporter on a machine that has the authoritative registered outputs to populate the sanitized snapshot.
