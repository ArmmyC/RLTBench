# Qwen3-Coder-30B-A3B-Instruct Output Manifest

## Git Tracking Policy

The raw benchmark output folders are not committed to Git.

Reason:

- `outputs/` is intentionally ignored by `.gitignore`.
- Run outputs contain raw model responses, extracted RTL, logs, and generated work directories.
- The committed artifacts are configs and reports that point to the authoritative Lanta output folders.

## Lanta Output Folders

| Benchmark / Mode | Output folder |
|---|---|
| VerilogEval smoke | `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162407Z` |
| VerilogEval pass@1 | `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162441Z` |
| VerilogEval pass@5 | `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162949Z` |

Each run folder contains the AGENTS-required artifacts:

```text
config_snapshot.yaml
run_metadata.json
report.md
results.jsonl
summary.json
summary.csv
raw_responses/
extracted_rtl/
logs/
error_logs/
```

## Committed Report Files

```text
reports/verilogeval_v2_qwen3_coder_30b_a3b_instruct_baseline.md
reports/qwen3_coder_30b_a3b_instruct_output_manifest.md
```
