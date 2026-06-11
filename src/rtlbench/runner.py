from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from rtlbench.adapters import ADAPTERS
from rtlbench.client import OpenAICompatibleClient
from rtlbench.config import RunConfig
from rtlbench.evaluator import IcarusEvaluator
from rtlbench.extraction import extract_rtl
from rtlbench.metrics import aggregate_results
from rtlbench.reporting import write_reports
from rtlbench.types import RunPaths, SampleResult

SYSTEM_PROMPT = (
    "You are an expert RTL designer. Generate correct, synthesizable Verilog/SystemVerilog "
    "code that satisfies the given specification. Return only the final code unless explanation "
    "is explicitly requested."
)


def run_benchmark(config: RunConfig, *, overwrite: bool = False) -> Path:
    adapter_type = ADAPTERS.get(config.benchmark_name)
    if not adapter_type:
        raise ValueError(f"Unknown benchmark {config.benchmark_name!r}; available: {', '.join(ADAPTERS)}")
    adapter = adapter_type(config.benchmark_root, config.split)
    tasks = list(adapter.load_tasks())
    if config.limit is not None:
        tasks = tasks[: config.limit]
    if not tasks:
        raise ValueError("The selected benchmark contains no tasks")

    paths = _create_run_paths(config.output_dir, config.benchmark_name, config.model, overwrite)
    evaluator = IcarusEvaluator(config.iverilog, config.evaluation_timeout)
    jobs = [(task, sample_id) for task in tasks for sample_id in range(config.samples_per_task)]
    rows: list[dict] = []
    print(f"Running {len(jobs)} samples across {len(tasks)} tasks with {config.workers} worker(s)")

    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        futures = {
            pool.submit(_run_sample, config, adapter, evaluator, paths, task, sample_id): (task.task_id, sample_id)
            for task, sample_id in jobs
        }
        for completed, future in enumerate(as_completed(futures), 1):
            task_id, sample_id = futures[future]
            try:
                row = future.result().to_dict()
            except Exception as exc:  # Preserve the run even for unexpected per-sample errors.
                row = SampleResult(
                    benchmark=config.benchmark_name,
                    task_id=task_id,
                    sample_id=sample_id,
                    model=config.model,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    max_tokens=config.max_tokens,
                    prompt_hash="",
                    failure_category="internal_error",
                ).to_dict()
                row["internal_error"] = repr(exc)
            rows.append(row)
            print(f"[{completed}/{len(jobs)}] {task_id} sample={sample_id} {row['failure_category']}")

    rows.sort(key=lambda row: (str(row["task_id"]), int(row["sample_id"])))
    summary = aggregate_results(rows)
    write_reports(paths.root, rows, summary)
    print(json.dumps(summary, indent=2))
    return paths.root


def _run_sample(config, adapter, evaluator, paths, task, sample_id: int) -> SampleResult:
    prompt = adapter.build_prompt(task)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    result = SampleResult(
        benchmark=config.benchmark_name,
        task_id=task.task_id,
        sample_id=sample_id,
        model=config.model,
        temperature=config.temperature,
        top_p=config.top_p,
        max_tokens=config.max_tokens,
        prompt_hash=prompt_hash,
        generation_extras=config.extra_body or None,
    )
    stem = f"{_safe_name(task.task_id)}__sample_{sample_id:03d}"
    raw_path = paths.raw / f"{stem}.txt"
    rtl_path = paths.rtl / f"{stem}.sv"
    log_path = paths.logs / f"{stem}.log"
    work_dir = paths.logs / stem
    work_dir.mkdir(parents=True, exist_ok=True)

    client = OpenAICompatibleClient(config.base_url, config.api_key, config.request_timeout, config.retries)
    try:
        try:
            generated = client.generate(
                model=config.model,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=config.temperature,
                top_p=config.top_p,
                max_tokens=config.max_tokens,
                extra_body=config.extra_body,
            )
        except Exception as exc:
            log_path.write_text(str(exc) + "\n", encoding="utf-8")
            result.error_log_path = str(log_path.relative_to(paths.root))
            return result
    finally:
        client.close()

    raw_path.write_text(generated.text, encoding="utf-8")
    result.raw_response_path = str(raw_path.relative_to(paths.root))
    result.latency_seconds = generated.latency_seconds
    result.token_usage = generated.usage
    if not generated.text.strip():
        result.failure_category = "empty_response"
        return result

    rtl = extract_rtl(generated.text)
    if rtl is None:
        result.failure_category = "code_extraction_failure"
        return result
    rtl_path.write_text(rtl, encoding="utf-8")
    result.extracted_rtl_path = str(rtl_path.relative_to(paths.root))
    evaluated = evaluator.evaluate(task, rtl_path, work_dir)
    log_path.write_text(evaluated.log, encoding="utf-8")
    result.compile_pass = evaluated.compile_pass
    result.sim_pass = evaluated.sim_pass
    result.final_pass = evaluated.final_pass
    result.failure_category = evaluated.failure_category
    result.error_log_path = str(log_path.relative_to(paths.root))
    return result


def _create_run_paths(base: Path, benchmark: str, model: str, overwrite: bool) -> RunPaths:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = base / f"{timestamp}__{benchmark}__{_safe_name(model)}"
    if root.exists() and not overwrite:
        raise FileExistsError(f"Output directory already exists: {root}")
    for child in (root, root / "raw", root / "rtl", root / "logs"):
        child.mkdir(parents=True, exist_ok=overwrite)
    return RunPaths(root, root / "raw", root / "rtl", root / "logs")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "unnamed"
