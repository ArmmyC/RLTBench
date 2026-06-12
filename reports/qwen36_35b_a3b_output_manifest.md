# Qwen36-35B-A3B Output Manifest

## Git Tracking Policy

The raw benchmark output folders are not committed to Git.

Reason:

- `outputs/` is intentionally ignored by `.gitignore`.
- Run outputs contain raw model responses, extracted RTL, logs, and generated work directories.
- The committed artifacts are configs and reports that point to the authoritative Lanta output folders.

## Lanta Output Folders

| Benchmark / Mode | Output folder |
|---|---|
| VerilogEval smoke | `outputs/verilogeval/qwen36-35b-a3b/20260612T125544Z` |
| VerilogEval pass@1 | `outputs/verilogeval/qwen36-35b-a3b/20260612T125618Z` |
| VerilogEval pass@5 | `outputs/verilogeval/qwen36-35b-a3b/20260612T132806Z` |
| RTLLM 2.0 pass@1 | `outputs/rtllm2/qwen36-35b-a3b/20260612T141752Z` |
| ProtocolLLM public lint | `outputs/protocollm/qwen36-35b-a3b/20260612T142333Z` |
| RTL-OPT lint | `outputs/rtlopt/qwen36-35b-a3b/20260612T144142Z` |
| RTL-OPT generic synthesis | `outputs/rtlopt/qwen36-35b-a3b/20260612T144440Z` |
| RTL-OPT equivalence | `outputs/rtlopt/qwen36-35b-a3b/20260612T143022Z` |

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
reports/verilogeval_v2_qwen36_35b_a3b_baseline.md
reports/rtllm2_qwen36_35b_a3b_baseline.md
reports/protocollm_qwen36_35b_a3b_public_lint_baseline.md
reports/rtlopt_qwen36_35b_a3b_yosys_equiv_baseline.md
reports/qwen36_27b_vs_qwen36_35b_a3b_verilogeval.md
reports/qwen36_27b_vs_qwen36_35b_a3b_public_benchmarks.md
reports/qwen36_35b_a3b_output_manifest.md
```
