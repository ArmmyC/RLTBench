# RTLBench

RTLBench is a reusable benchmark harness for evaluating RTL-generating models through an OpenAI-compatible API. Model access, benchmark loading, code extraction, simulation, and reporting are separate components so models and benchmark suites can be changed independently.

The first adapter supports VerilogEval-style JSONL/JSONL.GZ datasets. Planned adapters are RTLLM 2.0, ProtocolLLM, and RTL-OPT.

## Layout

```text
configs/                  Reproducible run configurations
scripts/                  Lanta setup and Slurm launch scripts
src/rtlbench/adapters/    Benchmark-specific task loaders and prompts
src/rtlbench/             API client, extraction, evaluation, metrics, reports
tests/                    Unit tests
benchmarks/               Local benchmark checkouts/data (gitignored)
outputs/                  Timestamped run artifacts (gitignored)
```

Every run writes:

```text
outputs/<timestamp>__<benchmark>__<model>/
  results.jsonl
  summary.json
  summary.csv
  raw/                     Original model responses
  rtl/                     Extracted RTL
  logs/                    Compile/simulation logs and work directories
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

## Run

Three-task smoke test:

```bash
.conda-env/bin/rtlbench --config configs/verilogeval.yaml \
  --limit 3 --samples-per-task 1 --temperature 0.2
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

## Adding A Benchmark

Implement `BenchmarkAdapter.load_tasks()` and `build_prompt()`, then register the adapter in `rtlbench.adapters.ADAPTERS`. Shared API calls, extraction, artifact handling, pass@k, and reporting require no changes. Add a benchmark-specific evaluator only when its official test flow cannot use the default Icarus compile-and-simulate path.

## Tests

```bash
.conda-env/bin/python -m pytest
```
