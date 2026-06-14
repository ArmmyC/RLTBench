# Baseline v0.2 Cross-Model Failure Matrix

## Coverage Summary

| Benchmark | Mode | Model | Run | Source | Rows |
|---|---|---|---|---|---:|
| verilogeval | pass1 | qwen36-27b | verilogeval_pass1_qwen36_27b | summary_only | 0 |
| verilogeval | pass1 | qwen36-35b-a3b | verilogeval_pass1_qwen36_35b_a3b | summary_only | 0 |
| verilogeval | pass1 | qwen3-coder-30b-a3b-instruct | verilogeval_pass1_qwen3_coder | summary_only | 0 |
| verilogeval | pass1 | qwen25-coder-32b | verilogeval_pass1_qwen25_coder | summary_only | 0 |
| verilogeval | pass1 | deepseek-coder-v2-lite-instruct | verilogeval_pass1_deepseek_coder | summary_only | 0 |
| verilogeval | pass5 | qwen36-27b | verilogeval_pass5_qwen36_27b | summary_only | 0 |
| verilogeval | pass5 | qwen36-35b-a3b | verilogeval_pass5_qwen36_35b_a3b | summary_only | 0 |
| verilogeval | pass5 | qwen3-coder-30b-a3b-instruct | verilogeval_pass5_qwen3_coder | summary_only | 0 |
| verilogeval | pass5 | qwen25-coder-32b | verilogeval_pass5_qwen25_coder | summary_only | 0 |
| verilogeval | pass5 | deepseek-coder-v2-lite-instruct | verilogeval_pass5_deepseek_coder | summary_only | 0 |
| rtllm2 | pass1 | qwen36-27b | rtllm2_pass1_qwen36_27b | summary_only | 0 |
| rtllm2 | pass1 | qwen36-35b-a3b | rtllm2_pass1_qwen36_35b_a3b | summary_only | 0 |
| rtllm2 | pass1 | qwen3-coder-30b-a3b-instruct | rtllm2_pass1_qwen3_coder | summary_only | 0 |
| rtllm2 | pass1 | qwen25-coder-32b | rtllm2_pass1_qwen25_coder | summary_only | 0 |
| rtllm2 | pass1 | deepseek-coder-v2-lite-instruct | rtllm2_pass1_deepseek_coder | summary_only | 0 |
| protocollm | lint | qwen36-27b | protocollm_lint_qwen36_27b | summary_only | 0 |
| protocollm | lint | qwen36-35b-a3b | protocollm_lint_qwen36_35b_a3b | summary_only | 0 |
| protocollm | lint | qwen3-coder-30b-a3b-instruct | protocollm_lint_qwen3_coder | summary_only | 0 |
| protocollm | lint | qwen25-coder-32b | protocollm_lint_qwen25_coder | summary_only | 0 |
| protocollm | lint | deepseek-coder-v2-lite-instruct | protocollm_lint_deepseek_coder | summary_only | 0 |
| rtlopt | lint | qwen36-27b | rtlopt_lint_qwen36_27b | summary_only | 0 |
| rtlopt | lint | qwen36-35b-a3b | rtlopt_lint_qwen36_35b_a3b | summary_only | 0 |
| rtlopt | lint | qwen3-coder-30b-a3b-instruct | rtlopt_lint_qwen3_coder | summary_only | 0 |
| rtlopt | lint | qwen25-coder-32b | rtlopt_lint_qwen25_coder | summary_only | 0 |
| rtlopt | lint | deepseek-coder-v2-lite-instruct | rtlopt_lint_deepseek_coder | summary_only | 0 |
| rtlopt | synthesis | qwen36-27b | rtlopt_synthesis_qwen36_27b | summary_only | 0 |
| rtlopt | synthesis | qwen36-35b-a3b | rtlopt_synthesis_qwen36_35b_a3b | summary_only | 0 |
| rtlopt | synthesis | qwen3-coder-30b-a3b-instruct | rtlopt_synthesis_qwen3_coder | summary_only | 0 |
| rtlopt | synthesis | qwen25-coder-32b | rtlopt_synthesis_qwen25_coder | summary_only | 0 |
| rtlopt | synthesis | deepseek-coder-v2-lite-instruct | rtlopt_synthesis_deepseek_coder | summary_only | 0 |
| rtlopt | equivalence | qwen36-27b | rtlopt_equivalence_qwen36_27b | summary_only | 0 |
| rtlopt | equivalence | qwen36-35b-a3b | rtlopt_equivalence_qwen36_35b_a3b | summary_only | 0 |
| rtlopt | equivalence | qwen3-coder-30b-a3b-instruct | rtlopt_equivalence_qwen3_coder | summary_only | 0 |
| rtlopt | equivalence | qwen25-coder-32b | rtlopt_equivalence_qwen25_coder | summary_only | 0 |
| rtlopt | equivalence | deepseek-coder-v2-lite-instruct | rtlopt_equivalence_deepseek_coder | summary_only | 0 |

## Failure Category Counts by Model

| Model | code_extraction_failure | compile_failure | equiv_failure | passed | simulation_failure | synthesis_failure | timeout |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen36-27b | 64 | 140 | 9 | 708 | 183 | 8 | 3 |
| qwen36-35b-a3b | 97 | 166 | 15 | 647 | 180 | 8 | 2 |
| qwen3-coder-30b-a3b-instruct | 13 | 127 | 16 | 549 | 355 | 3 | 2 |
| qwen25-coder-32b | 1 | 128 | 17 | 525 | 386 | 8 | 0 |
| deepseek-coder-v2-lite-instruct | 6 | 148 | 5 | 586 | 362 | 6 | 2 |

## Failure Category Counts by Benchmark

| Benchmark | code_extraction_failure | compile_failure | equiv_failure | passed | simulation_failure | synthesis_failure | timeout |
|---|---:|---:|---:|---:|---:|---:|---:|
| protocollm | 3 | 14 | 0 | 28 | 0 | 0 | 0 |
| rtllm2 | 2 | 35 | 0 | 86 | 25 | 0 | 2 |
| rtlopt | 12 | 17 | 62 | 469 | 0 | 33 | 7 |
| verilogeval | 164 | 643 | 0 | 2432 | 1441 | 0 | 0 |

## Per-Task Analysis

Per-task failure data is not available for this run. The summary-level baseline is still shown from registered summaries.

## Tasks Failed by All Available Models

Unavailable without per-task results.

## Tasks Solved by All Available Models

Unavailable without per-task results.

## Tasks Uniquely Solved by One Model

Unavailable without per-task results.

## Tasks Recovered by Pass@5

Unavailable without per-task results.

## Hardest Tasks

Unavailable without per-task results.

## Missing Data Warnings

- verilogeval_pass1_qwen36_27b: per-task results unavailable; using summary fallback
- verilogeval_pass1_qwen36_35b_a3b: per-task results unavailable; using summary fallback
- verilogeval_pass1_qwen3_coder: per-task results unavailable; using summary fallback
- verilogeval_pass1_qwen25_coder: per-task results unavailable; using summary fallback
- verilogeval_pass1_deepseek_coder: per-task results unavailable; using summary fallback
- verilogeval_pass5_qwen36_27b: per-task results unavailable; using summary fallback
- verilogeval_pass5_qwen36_35b_a3b: per-task results unavailable; using summary fallback
- verilogeval_pass5_qwen3_coder: per-task results unavailable; using summary fallback
- verilogeval_pass5_qwen25_coder: per-task results unavailable; using summary fallback
- verilogeval_pass5_deepseek_coder: per-task results unavailable; using summary fallback
- rtllm2_pass1_qwen36_27b: per-task results unavailable; using summary fallback
- rtllm2_pass1_qwen36_35b_a3b: per-task results unavailable; using summary fallback
- rtllm2_pass1_qwen3_coder: per-task results unavailable; using summary fallback
- rtllm2_pass1_qwen25_coder: per-task results unavailable; using summary fallback
- rtllm2_pass1_deepseek_coder: per-task results unavailable; using summary fallback
- protocollm_lint_qwen36_27b: per-task results unavailable; using summary fallback
- protocollm_lint_qwen36_35b_a3b: per-task results unavailable; using summary fallback
- protocollm_lint_qwen3_coder: per-task results unavailable; using summary fallback
- protocollm_lint_qwen25_coder: per-task results unavailable; using summary fallback
- protocollm_lint_deepseek_coder: per-task results unavailable; using summary fallback
- rtlopt_lint_qwen36_27b: per-task results unavailable; using summary fallback
- rtlopt_lint_qwen36_35b_a3b: per-task results unavailable; using summary fallback
- rtlopt_lint_qwen3_coder: per-task results unavailable; using summary fallback
- rtlopt_lint_qwen25_coder: per-task results unavailable; using summary fallback
- rtlopt_lint_deepseek_coder: per-task results unavailable; using summary fallback
- rtlopt_synthesis_qwen36_27b: per-task results unavailable; using summary fallback
- rtlopt_synthesis_qwen36_35b_a3b: per-task results unavailable; using summary fallback
- rtlopt_synthesis_qwen3_coder: per-task results unavailable; using summary fallback
- rtlopt_synthesis_qwen25_coder: per-task results unavailable; using summary fallback
- rtlopt_synthesis_deepseek_coder: per-task results unavailable; using summary fallback
- rtlopt_equivalence_qwen36_27b: per-task results unavailable; using summary fallback
- rtlopt_equivalence_qwen36_35b_a3b: per-task results unavailable; using summary fallback
- rtlopt_equivalence_qwen3_coder: per-task results unavailable; using summary fallback
- rtlopt_equivalence_qwen25_coder: per-task results unavailable; using summary fallback
- rtlopt_equivalence_deepseek_coder: per-task results unavailable; using summary fallback
