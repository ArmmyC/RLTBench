from __future__ import annotations

import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict

import yaml

from rtlbench.adapters import ADAPTERS
from rtlbench.client import OpenAICompatibleClient
from rtlbench.config import RunConfig
from rtlbench.evaluator import IcarusEvaluator, VerilatorLintEvaluator, YosysEquivalenceEvaluator, YosysPPAEvaluator
from rtlbench.extraction import extract_all_rtl_modules, extract_rtl
from rtlbench.metrics import aggregate_results
from rtlbench.prompt_profiles import DEFAULT_SYSTEM_PROMPT
from rtlbench.reporting import write_reports
from rtlbench.types import RunPaths, SampleResult

SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


def run_benchmark(config: RunConfig, *, overwrite: bool = False, notes: str = "") -> Path:
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
    _write_run_start_report(paths, config, len(tasks), notes)
    evaluator_name = config.evaluator_type or getattr(adapter, "evaluator_name", "icarus")
    if evaluator_name == "yosys_ppa":
        evaluator = YosysPPAEvaluator(config.iverilog, config.evaluation_timeout, use_abc=True)
    elif evaluator_name == "yosys_generic":
        evaluator = YosysPPAEvaluator(config.iverilog, config.evaluation_timeout, use_abc=False)
    elif evaluator_name == "yosys_equiv":
        evaluator = YosysEquivalenceEvaluator(config.iverilog, config.evaluation_timeout)
    elif evaluator_name == "verilator_lint":
        evaluator = VerilatorLintEvaluator(config.iverilog, config.evaluation_timeout)
    else:
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
    _write_run_final_report(paths, config, summary, notes)
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
    log_path = paths.error_logs / f"{stem}.log"
    work_dir = paths.logs / stem
    work_dir.mkdir(parents=True, exist_ok=True)

    client = OpenAICompatibleClient(config.base_url, config.api_key, config.request_timeout, config.retries)
    try:
        try:
            generated = client.generate(
                model=config.model,
                system_prompt=_system_prompt(config),
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

    if getattr(adapter, "extract_all_modules", False):
        rtl = extract_all_rtl_modules(generated.text, task.module_name)
    else:
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
    result.evaluation_metrics = evaluated.metrics or None
    return result


def _system_prompt(config: RunConfig) -> str:
    return config.system_prompt or SYSTEM_PROMPT


def _create_run_paths(base: Path, benchmark: str, model: str, overwrite: bool) -> RunPaths:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = base / _safe_name(benchmark) / _safe_name(model) / timestamp
    if root.exists() and not overwrite:
        raise FileExistsError(f"Output directory already exists: {root}")
    for child in (root, root / "raw_responses", root / "extracted_rtl", root / "logs", root / "error_logs"):
        child.mkdir(parents=True, exist_ok=overwrite)
    return RunPaths(root, root / "raw_responses", root / "extracted_rtl", root / "logs", root / "error_logs")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "unnamed"


def _write_run_start_report(paths: RunPaths, config: RunConfig, task_count: int, notes: str) -> None:
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "task_count": task_count,
        "python": sys.version,
        "argv": sys.argv,
        "notes": notes,
        "config": _serializable_config(config),
    }
    (paths.root / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (paths.root / "config_snapshot.yaml").write_text(
        yaml.safe_dump(_serializable_config(config), sort_keys=True), encoding="utf-8"
    )
    (paths.logs / "run_report.md").write_text(
        _render_report(metadata, summary=None), encoding="utf-8"
    )
    (paths.root / "report.md").write_text(
        _render_report(metadata, summary=None), encoding="utf-8"
    )


def _write_run_final_report(
    paths: RunPaths, config: RunConfig, summary: dict, notes: str
) -> None:
    metadata_path = paths.root / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "status": "finished",
            "summary": summary,
            "notes": notes,
            "config": _serializable_config(config),
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (paths.logs / "run_report.md").write_text(
        _render_report(metadata, summary=summary), encoding="utf-8"
    )
    (paths.root / "report.md").write_text(
        _render_report(metadata, summary=summary), encoding="utf-8"
    )


def _serializable_config(config: RunConfig) -> dict:
    data = asdict(config)
    data["benchmark_root"] = str(config.benchmark_root)
    data["output_dir"] = str(config.output_dir)
    if data.get("api_key"):
        data["api_key"] = "***"
    return data


def _render_report(metadata: dict, summary: dict | None) -> str:
    config = metadata["config"]
    lines = [
        f"# RTLBench Run Report",
        "",
        f"- Status: {metadata['status']}",
        f"- Started UTC: {metadata['started_utc']}",
    ]
    if metadata.get("finished_utc"):
        lines.append(f"- Finished UTC: {metadata['finished_utc']}")
    lines.extend(
        [
            f"- Benchmark: {config['benchmark_name']}",
            f"- Benchmark root: `{config['benchmark_root']}`",
            f"- Model: `{config['model']}`",
            f"- Prompt profile: `{config.get('prompt_profile') or 'legacy_default'}`",
            f"- Base URL: `{config['base_url']}`",
            f"- Tasks: {metadata['task_count']}",
            f"- Samples per task: {config['samples_per_task']}",
            f"- Temperature: {config['temperature']}",
            f"- Top-p: {config['top_p']}",
            f"- Max tokens: {config['max_tokens']}",
            f"- Workers: {config['workers']}",
            f"- Evaluator type: `{config.get('evaluator_type') or 'adapter_default'}`",
            f"- Evaluator executable: `{config['iverilog']}`",
        ]
    )
    if config.get("extra_body"):
        lines.extend(["", "## Generation Extras", "", "```json"])
        lines.append(json.dumps(config["extra_body"], indent=2, sort_keys=True))
        lines.append("```")
    if metadata.get("notes"):
        lines.extend(["", "## Notes", "", metadata["notes"]])
    lines.extend(["", "## What This Run Did", ""])
    lines.append(
        "Loaded benchmark tasks, called the OpenAI-compatible endpoint, extracted RTL, "
        "evaluated each sample with the configured benchmark evaluator, and wrote "
        "`results.jsonl`, `summary.json`, `summary.csv`, raw responses, RTL files, and logs."
    )
    if summary is not None:
        lines.extend(
            [
                "",
                "## Findings",
                "",
                f"- Samples: {summary['samples']}",
                f"- Tasks: {summary['tasks']}",
                f"- Syntax pass rate: {summary['syntax_pass_rate']:.4f}",
                f"- Functional pass rate: {summary['functional_pass_rate']:.4f}",
            ]
        )
        for key, value in summary["pass_at_k"].items():
            lines.append(f"- {key}: {value:.4f}")
        lines.append("- Failure categories: " + json.dumps(summary["failure_categories"], sort_keys=True))
    lines.extend(["", "## Command", "", "```text", " ".join(metadata["argv"]), "```", ""])
    return "\n".join(lines)
