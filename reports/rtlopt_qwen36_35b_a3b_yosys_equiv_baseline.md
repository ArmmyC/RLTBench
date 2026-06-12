# RTL-OPT Qwen36-35B-A3B Public Baselines

## Lint Run

- Output: `outputs/rtlopt/qwen36-35b-a3b/20260612T144142Z`
- Evaluation mode: Verilator lint-only
- Tasks: 40
- Result: 34 / 40 = 0.8500
- Failure categories: `{"passed": 34, "compile_failure": 5, "code_extraction_failure": 1}`

Detailed analyses:

```text
outputs/rtlopt/qwen36-35b-a3b/20260612T144142Z/logs/code_extraction_failure_analysis.md
outputs/rtlopt/qwen36-35b-a3b/20260612T144142Z/logs/compile_failure_analysis.md
```

## Generic Synthesis Run

- Output: `outputs/rtlopt/qwen36-35b-a3b/20260612T144440Z`
- Evaluation mode: Yosys generic synthesis
- Tasks: 40
- Result: 35 / 40 = 0.8750
- Failure categories: `{"passed": 35, "synthesis_failure": 3, "code_extraction_failure": 2}`
- Average generated generic cell ratio vs baseline: 1.6315
- Median generated generic cell ratio vs baseline: 1.0000

Detailed analyses:

```text
outputs/rtlopt/qwen36-35b-a3b/20260612T144440Z/logs/code_extraction_failure_analysis.md
outputs/rtlopt/qwen36-35b-a3b/20260612T144440Z/logs/synthesis_failure_analysis.md
```

## Equivalence Run

- Benchmark: RTL-OPT public repository
- Model: `qwen36-35b-a3b`
- Endpoint: `http://lanta-g-034:8000/v1`
- Output: `outputs/rtlopt/qwen36-35b-a3b/20260612T143022Z`
- Evaluation mode: Yosys generic synthesis plus equivalence against original suboptimal RTL
- Tasks: 40
- Samples per task: 1

## Equivalence Results

- Syntax/synthesis pass rate before equivalence: 0.8750
- Equivalence pass rate: 19 / 40 = 0.4750
- Failure categories: `{"passed": 19, "equiv_failure": 15, "synthesis_failure": 5, "timeout": 1}`

## Valid Optimization Signal

Among the 19 equivalence-passing tasks:

- Fewer generic cells than the original baseline: 6 / 19
- Equal generic cells to the original baseline: 9 / 19
- More generic cells than the original baseline: 4 / 19
- Average generic cell ratio vs baseline: 0.9003
- Median generic cell ratio vs baseline: 1.0000

Equivalence-passing tasks that also reduced generic cells:

```text
adder
comparator_2bit
mul_const
mux_4to1_16bit
mux_4to1_64bit
selector
```

Failed tasks:

```text
equiv_failure: add_sub, adder_carry, addr_calcu, alu_8bit, calculation, comparator_8bit, divider_8bit, fsm_encode, mac, mux_dead, saturating_add, sub_16bit, sub_4bit, sub_8bit, ticket_machine
synthesis_failure: alu_64bit, divider_32bit, divider_4bit, mux_encode, register
timeout: divider_16bit
```

Detailed analyses:

```text
outputs/rtlopt/qwen36-35b-a3b/20260612T143022Z/logs/equiv_failure_analysis.md
outputs/rtlopt/qwen36-35b-a3b/20260612T143022Z/logs/synthesis_failure_analysis.md
outputs/rtlopt/qwen36-35b-a3b/20260612T143022Z/logs/timeout_analysis.md
```

## Interpretation

This is the trustworthy RTL-OPT condition because it checks behavior preservation. `qwen36-35b-a3b` trails `qwen36-27b` on equivalence pass rate and on count of equivalence-passing improvements.
