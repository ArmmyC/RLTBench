# Qwen36-27B vs Qwen36-35B-A3B vs Qwen3-Coder VerilogEval v2 Comparison

## Scope

This comparison uses only VerilogEval v2 functional simulation results under matched benchmark settings.

Do not compare these numbers against lint-only ProtocolLLM or synthesis/equivalence RTL-OPT results as if they measure the same thing.

## Matched Settings

| Setting | pass@1 | pass@5 |
|---|---|---|
| Benchmark | VerilogEval v2 `dataset_spec-to-rtl` | VerilogEval v2 `dataset_spec-to-rtl` |
| Tasks | 156 | 156 |
| Samples per task | 1 | 5 |
| Temperature | 0.2 | 0.6 |
| Top-p | 0.95 | 0.95 |
| Max tokens | 2048 | 2048 |
| Evaluator | Icarus functional simulation | Icarus functional simulation |
| Repair retries | none | none |

## Results

| Model | Run | Samples | Syntax Pass | Functional/sample Pass | pass@5 |
|---|---|---:|---:|---:|---:|
| `qwen36-27b` | `outputs/verilogeval_v2_pass1/20260611T090440Z__verilogeval__qwen36-27b` | 156 | 0.8397 | 0.6154 | - |
| `qwen36-35b-a3b` | `outputs/verilogeval/qwen36-35b-a3b/20260612T125618Z` | 156 | 0.7564 | 0.5705 | - |
| `qwen3-coder-30b-a3b-instruct` | `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162441Z` | 156 | 0.8654 | 0.4808 | - |
| `qwen36-27b` | `outputs/verilogeval_v2_pass5/20260611T091009Z__verilogeval__qwen36-27b` | 780 | 0.7962 | 0.6115 | 0.7756 |
| `qwen36-35b-a3b` | `outputs/verilogeval/qwen36-35b-a3b/20260612T132806Z` | 780 | 0.7449 | 0.5615 | 0.7308 |
| `qwen3-coder-30b-a3b-instruct` | `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162949Z` | 780 | 0.8628 | 0.4846 | 0.5705 |

## Deltas

| Metric | qwen36-27b | qwen36-35b-a3b | qwen3-coder-30b-a3b-instruct |
|---|---:|---:|---:|
| pass@1 syntax | 0.8397 | 0.7564 | 0.8654 |
| pass@1 functional | 0.6154 | 0.5705 | 0.4808 |
| pass@5 syntax | 0.7962 | 0.7449 | 0.8628 |
| pass@5 sample functional | 0.6115 | 0.5615 | 0.4846 |
| pass@5 task recovery | 0.7756 | 0.7308 | 0.5705 |

## Failure Breakdown

### pass@1

| Model | Passed | Simulation Failure | Compile Failure | Extraction Failure |
|---|---:|---:|---:|---:|
| `qwen36-27b` | 96 | 35 | 17 | 8 |
| `qwen36-35b-a3b` | 89 | 29 | 26 | 12 |
| `qwen3-coder-30b-a3b-instruct` | 75 | 60 | 20 | 1 |

### pass@5 Samples

| Model | Passed | Simulation Failure | Compile Failure | Extraction Failure |
|---|---:|---:|---:|---:|
| `qwen36-27b` | 477 | 144 | 104 | 55 |
| `qwen36-35b-a3b` | 438 | 143 | 121 | 78 |
| `qwen3-coder-30b-a3b-instruct` | 378 | 295 | 101 | 6 |

## Conclusion

On VerilogEval v2, `qwen36-27b` remains the strongest functional baseline under the matched settings tested so far.

- `qwen36-27b` has the best pass@1 functional correctness and pass@5 task recovery.
- `qwen36-35b-a3b` remains second on functional pass@1 and pass@5.
- `qwen3-coder-30b-a3b-instruct` has the best syntax pass rate, but lower functional correctness after simulation.

Recommended next comparison step: run the rest of the public benchmark sequence for `qwen3-coder-30b-a3b-instruct` before updating the full public benchmark comparison.
