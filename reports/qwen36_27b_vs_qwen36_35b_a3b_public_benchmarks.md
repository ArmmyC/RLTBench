# Qwen36-27B vs Qwen36-35B-A3B Public RTL Benchmark Comparison

## Scope

This report compares `qwen36-27b` and `qwen36-35b-a3b` on public RTL benchmarks currently available in the harness.

Comparison rule:

- Functional simulation results are compared with functional simulation results.
- ProtocolLLM public lint is reported separately as lint-only.
- RTL-OPT equivalence is reported separately as behavior-preserving optimization evidence.

## Matched Settings Audit

| Benchmark / Mode | Same benchmark? | samples_per_task | Temperature | Top-p | Max tokens | Notes |
|---|---|---:|---:|---:|---:|---|
| VerilogEval v2 pass@1 | yes, VerilogEval v2 `dataset_spec-to-rtl` | 1 | 0.2 | 0.95 | 2048 | qwen36-27b run predates `run_metadata.json`; settings are from the committed baseline report and run command record |
| VerilogEval v2 pass@5 | yes, VerilogEval v2 `dataset_spec-to-rtl` | 5 | 0.6 | 0.95 | 2048 | qwen36-27b run predates `run_metadata.json`; settings are from the committed baseline report and run command record |
| RTLLM 2.0 pass@1 | yes, RTLLM 2.0 public benchmark | 1 | 0.2 | 0.95 | 4096 | verified from both run metadata files |
| ProtocolLLM public lint | yes, ProtocolLLM public prompts | 1 | 0.2 | 0.95 | 4096 | verified from both run metadata files; lint-only |
| RTL-OPT lint | yes, RTL-OPT public benchmark | 1 | 0.2 | 0.95 | 4096 | lint-only |
| RTL-OPT generic synthesis | yes, RTL-OPT public benchmark | 1 | 0.2 | 0.95 | 4096 | synthesis-only |
| RTL-OPT equivalence | yes, RTL-OPT public benchmark | 1 | 0.2 | 0.95 | 4096 | verified from both run metadata files; behavior-preserving optimization condition |

The comparison below reports the two model results side by side only within the same benchmark and evaluation mode.

## Output Artifact Tracking

Raw output folders are preserved on Lanta and are not committed to Git because `outputs/` is intentionally gitignored by repo policy. The committed artifacts are the benchmark configs, summary reports, and this comparison report. The exact output directories are listed in the tables below and in `reports/qwen36_35b_a3b_output_manifest.md`.

## Functional RTL Generation

| Benchmark | Metric | qwen36-27b | qwen36-35b-a3b | Delta |
|---|---|---:|---:|---:|
| VerilogEval v2 | pass@1 functional | 0.6154 | 0.5705 | -0.0449 |
| VerilogEval v2 | pass@5 task recovery | 0.7756 | 0.7308 | -0.0449 |
| RTLLM 2.0 | pass@1 functional | 0.6000 | 0.6000 | 0.0000 |

## Syntax / Compile Reliability

| Benchmark | qwen36-27b | qwen36-35b-a3b | Delta |
|---|---:|---:|---:|
| VerilogEval v2 pass@1 syntax | 0.8397 | 0.7564 | -0.0833 |
| VerilogEval v2 pass@5 syntax | 0.7962 | 0.7449 | -0.0513 |
| RTLLM 2.0 syntax | 0.7000 | 0.7800 | +0.0800 |

## Lint-Only Protocol Result

| Benchmark | qwen36-27b | qwen36-35b-a3b | Delta |
|---|---:|---:|---:|
| ProtocolLLM public lint | 0.7778 | 0.2222 | -0.5556 |

This is lint-only. It does not measure protocol functional correctness.

## RTL-OPT Behavior-Preserving Optimization

| Metric | qwen36-27b | qwen36-35b-a3b | Delta |
|---|---:|---:|---:|
| RTL-OPT lint pass | 0.9250 | 0.8500 | -0.0750 |
| RTL-OPT generic synthesis pass | 0.9000 | 0.8750 | -0.0250 |
| RTL-OPT equivalence pass | 0.6250 | 0.4750 | -0.1500 |
| Equiv-passing tasks with fewer generic cells | 9 / 25 | 6 / 19 | - |
| Average generic cell ratio among equiv-passing tasks | 0.9124 | 0.9003 | -0.0121 |

The 35B-A3B model has a slightly better average cell ratio among the tasks that pass equivalence, but fewer tasks reach equivalence, so its trustworthy optimization coverage is lower.

## Conclusion

`qwen36-27b` remains the stronger public RTL benchmark baseline overall.

- It is better on VerilogEval v2 pass@1 and pass@5.
- It ties `qwen36-35b-a3b` on RTLLM 2.0 functional pass@1.
- It is much better on ProtocolLLM public lint.
- It is better on RTL-OPT equivalence pass rate and valid-improved task count.

The only clear advantage for `qwen36-35b-a3b` in this set is RTLLM syntax pass rate, where it improves from 0.7000 to 0.7800 while tying functional pass@1.

Recommended next model: `qwen3-coder-30b-a3b`, using the same public benchmark sequence.
