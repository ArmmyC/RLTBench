# Qwen36-27B RTL Benchmark Summary

## Scope

This report summarizes the current RTL benchmark baseline for `qwen36-27b` served on Lanta through the vLLM OpenAI-compatible API.

- Updated: 2026-06-12
- Model: `qwen36-27b`
- Latest endpoint used: `http://lanta-g-165:8000/v1`
- Runtime setting: Qwen hidden thinking disabled via `chat_template_kwargs.enable_thinking=false`
- Baseline rule: no repair retries, no manual RTL correction, no task-specific prompt tuning folded into baseline scores

Detailed reports:

- `reports/verilogeval_v2_qwen36_27b_baseline.md`
- `reports/verilogeval_v2_qwen36_35b_a3b_baseline.md`
- `reports/qwen36_27b_vs_qwen36_35b_a3b_verilogeval.md`
- `reports/qwen36_27b_vs_qwen36_35b_a3b_public_benchmarks.md`
- `reports/rtllm2_qwen36_27b_baseline.md`
- `reports/rtllm2_qwen36_35b_a3b_baseline.md`
- `reports/protocollm_qwen36_27b_public_lint_baseline.md`
- `reports/protocollm_qwen36_35b_a3b_public_lint_baseline.md`
- `reports/rtlopt_qwen36_27b_public_lint_baseline.md`
- `reports/rtlopt_qwen36_27b_yosys_generic_baseline.md`
- `reports/rtlopt_qwen36_27b_yosys_equiv_baseline.md`
- `reports/rtlopt_qwen36_35b_a3b_yosys_equiv_baseline.md`

## Headline Results

| Benchmark | Evaluation | Tasks | Samples | Syntax/Synth Pass | Functional/Equiv Pass | pass@5 | Output |
|---|---|---:|---:|---:|---:|---:|---|
| VerilogEval v2 | Icarus functional simulation | 156 | 156 | 0.8397 | 0.6154 | - | `outputs/verilogeval_v2_pass1/20260611T090440Z__verilogeval__qwen36-27b` |
| VerilogEval v2 | Icarus functional simulation | 156 | 780 | 0.7962 | 0.6115 | 0.7756 | `outputs/verilogeval_v2_pass5/20260611T091009Z__verilogeval__qwen36-27b` |
| VerilogEval v2 (`qwen36-35b-a3b`) | Icarus functional simulation | 156 | 156 | 0.7564 | 0.5705 | - | `outputs/verilogeval/qwen36-35b-a3b/20260612T125618Z` |
| VerilogEval v2 (`qwen36-35b-a3b`) | Icarus functional simulation | 156 | 780 | 0.7449 | 0.5615 | 0.7308 | `outputs/verilogeval/qwen36-35b-a3b/20260612T132806Z` |
| RTLLM 2.0 | Icarus functional simulation | 50 | 50 | 0.7000 | 0.6000 | - | `outputs/rtllm2_pass1/20260611T133005Z__rtllm2__qwen36-27b` |
| RTLLM 2.0 (`qwen36-35b-a3b`) | Icarus functional simulation | 50 | 50 | 0.7800 | 0.6000 | - | `outputs/rtllm2/qwen36-35b-a3b/20260612T141752Z` |
| ProtocolLLM public | Verilator lint only | 9 | 9 | 0.7778 | lint-only | - | `outputs/protocollm_lint_pass1/20260611T162344Z__protocollm__qwen36-27b` |
| ProtocolLLM public (`qwen36-35b-a3b`) | Verilator lint only | 9 | 9 | 0.2222 | lint-only | - | `outputs/protocollm/qwen36-35b-a3b/20260612T142333Z` |
| RTL-OPT | Verilator lint only | 40 | 40 | 0.9250 | lint-only | - | `outputs/rtlopt_lint_pass1/20260612T045332Z__rtlopt__qwen36-27b` |
| RTL-OPT | Yosys generic synthesis | 40 | 40 | 0.9000 | synth-only | - | `outputs/rtlopt_yosys_pass1/20260612T052731Z__rtlopt__qwen36-27b` |
| RTL-OPT | Yosys equivalence + generic cells | 40 | 40 | 0.9000 | 0.6250 | - | `outputs/rtlopt_equiv_pass1/20260612T060533Z__rtlopt__qwen36-27b` |
| RTL-OPT (`qwen36-35b-a3b`) | Verilator lint only | 40 | 40 | 0.8500 | lint-only | - | `outputs/rtlopt/qwen36-35b-a3b/20260612T144142Z` |
| RTL-OPT (`qwen36-35b-a3b`) | Yosys generic synthesis | 40 | 40 | 0.8750 | synth-only | - | `outputs/rtlopt/qwen36-35b-a3b/20260612T144440Z` |
| RTL-OPT (`qwen36-35b-a3b`) | Yosys equivalence + generic cells | 40 | 40 | 0.8750 | 0.4750 | - | `outputs/rtlopt/qwen36-35b-a3b/20260612T143022Z` |

## Benchmark Confidence

| Benchmark | What It Proves | Confidence | Caveat |
|---|---|---|---|
| VerilogEval v2 | Generated RTL passes official testbench simulation | High | Testbench coverage is benchmark-defined, not formal equivalence |
| RTLLM 2.0 | Generated RTL passes official testbench simulation | High | Some tasks require staged support files and all-module extraction |
| ProtocolLLM public | Generated RTL passes Verilator lint | Medium-low | Public repo lacks the functional waveform/UVM tests described in the paper |
| RTL-OPT lint | Generated RTL is Verilator-lint clean | Medium | Does not prove behavior or optimization |
| RTL-OPT Yosys generic | Generated RTL synthesizes and has structural metrics | Medium-high | Generic cells are not official Nangate PPA |
| RTL-OPT Yosys equivalence | Generated RTL synthesizes and is proven equivalent to original RTL | High for behavior, medium for PPA | Two tasks timed out; official ABC/Nangate area mapping stalled in this environment |

## Failure Modes

### VerilogEval v2 Pass@1

| Category | Count |
|---|---:|
| passed | 96 |
| simulation_failure | 35 |
| compile_failure | 17 |
| code_extraction_failure | 8 |

Key findings:

- All 8 extraction failures were truncated reasoning-in-comments responses that consumed the full `2048` completion-token budget.
- 16/17 compile failures were model-generated invalid RTL; `Prob099_m2014_q6c` appears to be a benchmark port-name inconsistency.
- Simulation failures mostly involve sequential behavior, FSM/protocol logic, reset behavior, or timing.

### RTLLM 2.0

| Category | Count |
|---|---:|
| passed | 30 |
| compile_failure | 14 |
| simulation_failure | 4 |
| code_extraction_failure | 1 |
| timeout | 1 |

Key findings:

- RTLLM required all-module extraction because valid responses may include helper modules.
- Compile failures dominate over simulation failures, especially on larger arithmetic/interface-heavy designs.

### ProtocolLLM Public Lint

| Category | Count |
|---|---:|
| passed | 7 |
| compile_failure | 2 |

This is lint-only and should not be compared directly against VerilogEval or RTLLM functional pass rates.

### RTL-OPT Equivalence

| Category | Count |
|---|---:|
| passed | 25 |
| equiv_failure | 9 |
| synthesis_failure | 4 |
| timeout | 2 |

Among the 25 equivalence-passing RTL-OPT tasks:

- 9/25 also reduced generic cell count versus the original RTL
- 12/25 matched the original generic cell count
- 4/25 increased generic cell count
- Average generic cell ratio vs baseline: 0.9124
- Median generic cell ratio vs baseline: 1.0000

Equivalence-passing tasks with fewer generic cells:

```text
adder
comparator_2bit
comparator_4bit
comparator_8bit
mul_const
mul_subexpression
mux_4to1_16bit
mux_4to1_64bit
sub_16bit
```

## Interpretation

`qwen36-27b` shows real RTL generation capability:

- Functional pass@1 is consistent across VerilogEval v2 and RTLLM 2.0: about 0.60 to 0.62.
- VerilogEval pass@5 reaches 0.7756, so sampling recovers many tasks.
- RTL-OPT lint/synthesis rates are high, but equivalence lowers the trustworthy optimization score to 0.6250.
- Only 9/40 RTL-OPT tasks currently qualify as behavior-preserving and structurally improved under generic Yosys cells.

The first matched multi-model VerilogEval comparison shows `qwen36-27b` ahead of `qwen36-35b-a3b`:

- pass@1 functional: `0.6154` vs `0.5705`
- pass@5 task recovery: `0.7756` vs `0.7308`
- The 35B-A3B model had more extraction and compile failures under the same settings.

Across the broader public comparison, `qwen36-35b-a3b` ties RTLLM functional pass@1 at `0.6000` and improves RTLLM syntax pass rate, but trails on VerilogEval, ProtocolLLM public lint, and RTL-OPT equivalence.

The recurring weak spots are:

- invalid procedural constructs at module scope
- malformed module declarations in occasional outputs
- sequential/FSM/protocol timing mistakes
- reset behavior
- long arithmetic or memory-heavy tasks
- over-commented/truncated reasoning when token budget is too low or hidden thinking is not disabled

## Known Limitations

- ProtocolLLM is currently public lint-only because the public repo does not include the functional waveform/UVM testbenches described by the paper.
- RTL-OPT official Nangate area scoring is not fully reproduced because conda Yosys/ABC stalled during Liberty technology mapping, even on small examples.
- RTL-OPT equivalence uses Yosys generic synthesis plus equivalence against the original suboptimal RTL. This is stricter than lint/synthesis-only but not a full official PPA flow.
- RTL-OPT had two equivalence timeouts: `divider_16bit` and `divider_32bit`.

## Recommended Next Experiments

1. Run `qwen3-coder-30b-a3b` through the same public benchmark sequence.
2. Run RTLLM 2.0 pass@5 for both models if sampling recovery matters for the target workflow.
3. Try an RTL-OPT prompt variant focused on preserving exact behavior and minimizing generic cells, reported as a separate prompted condition.
4. Investigate a more robust open-source PPA flow for RTL-OPT area, either by fixing the Yosys/ABC Liberty mapping stall or using an alternative synthesis stack.
5. If ProtocolLLM functional tests become available, add them and replace the current lint-only condition.
