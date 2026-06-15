# RTLBench

RTLBench is a reusable benchmark harness for evaluating RTL-generating models through an OpenAI-compatible API. Model access, benchmark loading, code extraction, simulation, and reporting are separate components so models and benchmark suites can be changed independently.

The harness includes adapters for VerilogEval v2, RTLLM 2.0, ProtocolLLM public lint, and RTL-OPT lint/synthesis/equivalence.

## Layout

```text
configs/                  Reproducible run configurations
scripts/                  Lanta setup and Slurm launch scripts
src/rtlbench/adapters/    Benchmark-specific task loaders and prompts
src/rtlbench/             API client, extraction, evaluation, metrics, reports
tests/                    Unit tests
runs/                     Committed baseline run registry
dashboard/                Generated static Baseline v0.1 dashboard
benchmarks/               Local benchmark checkouts/data (gitignored)
outputs/                  Timestamped run artifacts (gitignored)
```

Every run writes:

```text
outputs/<benchmark>/<model>/<timestamp>/
  config_snapshot.yaml
  run_metadata.json
  report.md
  results.jsonl
  summary.json
  summary.csv
  raw_responses/            Original model responses
  extracted_rtl/            Extracted RTL
  logs/
    run_report.md           Human-readable run log: config, notes, findings
    */                      Per-sample evaluator work directories
  error_logs/
    *.log                   Compile/simulation/synthesis/equivalence logs
```

## Lanta Setup

The deployment path is:

```text
/project/zz992000-zdevb/zz992005/ub127/SiliconCraft/benchmark
```

Create the isolated Conda environment and install RTLBench plus Icarus Verilog:

```bash
cd /project/zz992000-zdevb/zz992005/ub127/SiliconCraft/benchmark
bash scripts/setup_lanta.sh
```

Clone the official VerilogEval repository under `benchmarks/verilog-eval`:

```bash
git clone https://github.com/NVlabs/verilog-eval.git benchmarks/verilog-eval
```

The adapter natively loads the 156 VerilogEval v2 prompt, testbench, and reference-module triples in `dataset_spec-to-rtl`. It also accepts an original VerilogEval `.jsonl` or `.jsonl.gz` file whose rows contain `prompt`, `test` (or `testbench`), and preferably `task_id`.

## Configuration

Connection values can be supplied through YAML, CLI arguments, or environment variables. Environment variables are useful for secrets and model swaps:

```bash
export OPENAI_BASE_URL=http://<vllm-node>:8000/v1
export OPENAI_API_KEY=EMPTY
export OPENAI_MODEL=qwen36-27b
export BENCHMARK_ROOT=$PWD/benchmarks/verilogeval
```

The legacy `QWEN_BASE_URL`, `QWEN_API_KEY`, and `QWEN_MODEL` variables are also accepted. Do not commit API keys to YAML.

Model presets live in `configs/models.yaml`. Use `--model-preset` to swap served model names without changing benchmark settings:

```bash
.conda-env/bin/rtlbench --config configs/verilogeval.yaml \
  --model-preset qwen36-35b-a3b \
  --base-url http://<vllm-node>:8000/v1 \
  --limit 3 --samples-per-task 1
```

## Run

Three-task smoke test:

```bash
.conda-env/bin/rtlbench --config configs/verilogeval.yaml \
  --limit 3 --samples-per-task 1 --temperature 0.2 \
  --notes "Smoke test after changing prompt or evaluator behavior."
```

Larger pass@5 run:

```bash
.conda-env/bin/rtlbench --config configs/verilogeval.yaml \
  --samples-per-task 5 --temperature 0.6 --workers 4
```

Submit the runner through Slurm. If `OPENAI_BASE_URL` is unset, the script discovers the node of a running `vllm-model` job:

```bash
mkdir -p logs
sbatch --export=ALL,OPENAI_MODEL=qwen36-27b scripts/run_lanta.sbatch \
  --limit 3 --samples-per-task 1
```

The benchmark job itself is CPU-only; the four A100 GPUs remain assigned to the vLLM serving job. This keeps generation reusable across benchmark suites and avoids loading a second model copy.

## Experiment Logs

Each run automatically writes `run_metadata.json` and `logs/run_report.md` inside its output directory. Use `--notes` to record the run intent or hypothesis.

Human-curated experiment notes live under `logs/`, for example `logs/2026-06-11-verilogeval-v2-qwen36.md`.

## Adding A Benchmark

Implement `BenchmarkAdapter.load_tasks()` and `build_prompt()`, then register the adapter in `rtlbench.adapters.ADAPTERS`. Shared API calls, extraction, artifact handling, pass@k, and reporting require no changes. Add a benchmark-specific evaluator only when its official test flow cannot use the default Icarus compile-and-simulate path.

## Tests

```bash
.conda-env/bin/python -m pytest
```

## Baseline v0.1 Reproducibility Package

Baseline v0.1 freezes the current five-model public RTL comparison in `runs/index.yaml`. Generated Markdown, JSON, CSV, and static HTML artifacts come from this registry rather than hand-maintained comparison tables.

Regenerate the package from the repository root:

```bash
python scripts/generate_comparison_report.py --registry runs/index.yaml --baseline baseline_v0_1
python scripts/analyze_cross_model_failures.py --registry runs/index.yaml --baseline baseline_v0_1
python scripts/build_dashboard.py --registry runs/index.yaml --baseline baseline_v0_1
python -m pytest
```

Open `dashboard/index.html` directly in a browser; it has no server or external CDN dependency.

Historical LANTA output folders are not present in every checkout. The registry prefers an accessible `summary.json`, otherwise it uses an explicitly labeled `manual_summary` transcribed from committed reports/manifests. Missing `results.jsonl` files produce warnings and an empty per-task failure state rather than fabricated data.

See:

- `docs/baseline_v0.1.md` for registry maintenance and generated artifacts.
- `docs/lanta_single_model_workflow.md` for the serving/benchmark ownership boundary.

## Baseline v0.2 Per-Task Failure Matrix

Baseline v0.2 adds a lightweight, commit-safe per-task layer without changing the frozen v0.1 run selection. Generate sanitized artifacts first, then build the v0.2 matrix and dashboard:

```bash
python scripts/export_per_task_results.py --registry runs/index.yaml --baseline baseline_v0_1 --output-dir artifacts/baseline_v0.2
python scripts/audit_baseline_consistency.py --registry runs/index.yaml --baseline baseline_v0_1 --per-task-artifacts artifacts/baseline_v0.2/per_task_results.jsonl --output-md reports/baseline_v0.2_consistency_audit.md --output-csv reports/baseline_v0.2_consistency_audit.csv
python scripts/analyze_cross_model_failures.py --registry runs/index.yaml --baseline baseline_v0_1 --per-task-artifacts artifacts/baseline_v0.2/per_task_results.jsonl --output-md reports/baseline_v0.2_failure_matrix.md --output-csv reports/baseline_v0.2_failure_matrix.csv
python scripts/build_dashboard.py --registry runs/index.yaml --baseline baseline_v0_1
python -m pytest
```

Analysis uses accessible live `results.jsonl` first, sanitized artifacts second, and registered summaries last. Pass `--prefer-artifacts` to the analysis or dashboard command for a portable artifact-only view. The exporter never includes prompts, model responses, RTL, error-log contents, credentials, or paths to those raw artifacts.

Before tagging a baseline, the consistency audit compares sanitized row and failure-category counts for every `source_run_id` against the summaries loaded from `runs/index.yaml`. Mismatches and missing run artifacts are warnings by default so the report can be reviewed; pass `--strict` to make either condition return a nonzero exit status. The audit is diagnostic and never rewrites registry summaries.

See `docs/baseline_v0.2_per_task_failure_matrix.md` for the schema, source precedence, and limitations.

## Baseline v0.3 Prompt Experiments

Baseline v0.2 is frozen. Baseline v0.3 experiments compare prompt profiles on qwen36-27b only and keep their outputs separate from the v0.1/v0.2 reports and artifacts.

Run a three-task VerilogEval smoke with the strict RTL-only profile:

```bash
.conda-env/bin/rtlbench \
  --config configs/experiments/v0.3_qwen36_27b_verilogeval_prompt_smoke.yaml \
  --base-url "$OPENAI_BASE_URL" \
  --prompt-profile strict_rtl_only \
  --output-dir outputs/experiments/v0.3_prompt_profiles/verilogeval/strict_rtl_only \
  --notes "v0.3 strict_rtl_only VerilogEval smoke"
```

Omitting `--prompt-profile` preserves the historical runner behavior. See `docs/experiments/v0.3_qwen36_27b_prompt_experiments.md` for profile definitions, matched-setting rules, and the smoke-first expansion policy.

Model serving, swapping, SSH/Slurm orchestration, OpenWebUI, and LiteLLM belong to the separate `Lanta-LLM-Hosting` repository, not this benchmark repository.
