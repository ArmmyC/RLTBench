# VerilogEval v2 Qwen3-Coder-30B-A3B-Instruct Baseline

## Run

- Benchmark: VerilogEval v2 `dataset_spec-to-rtl`
- Model preset: `qwen3-coder-30b-a3b-instruct`
- Served model ID: `qwen3-coder-30b-a3b`
- Endpoint: `http://lanta-g-028:8000/v1`
- Prompt condition: same neutral benchmark prompt as the qwen36 baselines
- Hidden thinking: disabled with `chat_template_kwargs.enable_thinking=false`
- Evaluator: Icarus Verilog functional simulation
- Date: 2026-06-12

The Lanta preset serves the Hugging Face model `Qwen/Qwen3-Coder-30B-A3B-Instruct` under the API model ID `qwen3-coder-30b-a3b`. The benchmark config keeps a `qwen3-coder-30b-a3b-instruct` preset alias that maps to that served ID.

## Smoke

- Output: `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162407Z`
- Tasks: 3
- Samples: 3
- Samples per task: 1
- Temperature: 0.2
- Top-p: 0.95
- Max tokens: 2048
- Result: 3 / 3 passed

## Pass@1

- Output: `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162441Z`
- Tasks: 156
- Samples: 156
- Samples per task: 1
- Temperature: 0.2
- Top-p: 0.95
- Max tokens: 2048
- Syntax pass rate: 0.8654
- Functional pass@1: 0.4808

Failure breakdown:

```json
{
  "passed": 75,
  "simulation_failure": 60,
  "compile_failure": 20,
  "code_extraction_failure": 1
}
```

## Pass@5

- Output: `outputs/verilogeval/qwen3-coder-30b-a3b/20260612T162949Z`
- Tasks: 156
- Samples: 780
- Samples per task: 5
- Temperature: 0.6
- Top-p: 0.95
- Max tokens: 2048
- Syntax pass rate: 0.8628
- Sample functional pass rate: 0.4846
- pass@5: 0.5705

Pass@k:

| Metric | Score |
|---|---:|
| pass@1 | 0.4846 |
| pass@2 | 0.5231 |
| pass@3 | 0.5442 |
| pass@4 | 0.5590 |
| pass@5 | 0.5705 |

Failure breakdown:

```json
{
  "passed": 378,
  "simulation_failure": 295,
  "compile_failure": 101,
  "code_extraction_failure": 6
}
```

## Output Artifacts

Each run folder contains:

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

## Interpretation

Under identical VerilogEval v2 settings, `qwen3-coder-30b-a3b-instruct` has the best syntax pass rate among the three tested models, but it trails both qwen36 baselines on functional pass@1 and pass@5. The gap is mainly functional correctness after syntax succeeds, especially simulation failures on harder sequential/FSM-style tasks.

This is a baseline result only. Prompt engineering or repair loops should be reported as separate benchmark conditions.
