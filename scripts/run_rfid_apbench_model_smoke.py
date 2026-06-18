from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from evaluate_rfid_apbench_candidates import (  # noqa: E402
    CandidateEvaluationRow,
    ToolAvailability,
    detect_tools,
    evaluate_candidates,
)
from rtlbench.adapters.rfid_apbench import RFIDAPBenchAdapter, RFIDAPBenchTaskInfo  # noqa: E402
from rtlbench.area_activity_scoring import validate_sanitized_record  # noqa: E402
from rtlbench.client import OpenAICompatibleClient  # noqa: E402
from rtlbench.extraction import extract_all_rtl_modules  # noqa: E402


DEFAULT_MODEL = "qwen36-27b"
DEFAULT_PROMPT_PROFILE = "neutral_baseline"
SYSTEM_PROMPT = (
    "You generate synthesizable SystemVerilog RTL for public benchmark tasks. "
    "Return only complete Verilog/SystemVerilog modules needed for the requested top module."
)
REPORT_FIELDS = [
    "benchmark",
    "task_id",
    "sample_id",
    "model",
    "prompt_profile",
    "endpoint_status",
    "generation_status",
    "extraction_status",
    "candidate_file_available",
    "compile_pass",
    "correctness_pass",
    "synth_pass",
    "timing_status",
    "area_metric_available",
    "activity_metric_available",
    "reference_area",
    "generated_area",
    "area_unit",
    "reference_activity",
    "generated_activity",
    "activity_metric",
    "area_score",
    "activity_score",
    "score",
    "score_status",
    "failure_category",
    "toolchain_id",
    "workload_id",
    "notes",
]


@dataclass(frozen=True)
class EndpointConfig:
    base_url: str | None
    credential: str | None
    model: str
    timeout_seconds: float

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.credential)

    @property
    def status(self) -> str:
        return "available" if self.available else "unavailable"

    @property
    def sanitized_endpoint(self) -> str:
        return sanitize_endpoint(self.base_url)

    @property
    def missing_labels(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not self.base_url:
            missing.append("base_url")
        if not self.credential:
            missing.append("credential")
        return tuple(missing)


@dataclass(frozen=True)
class GenerationRecord:
    task_id: str
    generation_status: str
    extraction_status: str
    candidate_file_available: bool
    latency_seconds: float | None
    notes: str


@dataclass
class ModelSmokeRow:
    benchmark: str
    task_id: str
    sample_id: int
    model: str
    prompt_profile: str
    endpoint_status: str
    generation_status: str
    extraction_status: str
    candidate_file_available: bool
    compile_pass: bool
    correctness_pass: bool
    synth_pass: bool
    timing_status: str
    area_metric_available: bool
    activity_metric_available: bool
    reference_area: float | None
    generated_area: float | None
    area_unit: str | None
    reference_activity: float | None
    generated_activity: float | None
    activity_metric: str | None
    area_score: float | None
    activity_score: float | None
    score: float | None
    score_status: str
    failure_category: str
    toolchain_id: str
    workload_id: str
    notes: str

    def sanitized_dict(self) -> dict[str, object]:
        data = asdict(self)
        validate_sanitized_record(data)
        return data

    def csv_dict(self) -> dict[str, str]:
        data = self.sanitized_dict()
        return {key: "" if data[key] is None else str(data[key]) for key in REPORT_FIELDS}


def load_endpoint_config(
    env: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> EndpointConfig:
    if env is None:
        env = {**load_local_env_file(env_file or REPO_ROOT / ".env"), **os.environ}
    elif env_file is not None:
        env = {**load_local_env_file(env_file), **env}
    timeout = _float_env(env.get("QWEN_TIMEOUT") or env.get("OPENAI_TIMEOUT"), 120.0)
    return EndpointConfig(
        base_url=_first_nonempty(env.get("QWEN_BASE_URL"), env.get("OPENAI_BASE_URL")),
        credential=_first_nonempty(env.get("QWEN_API_KEY"), env.get("OPENAI_API_KEY")),
        model=_first_nonempty(env.get("QWEN_MODEL"), env.get("OPENAI_MODEL")) or DEFAULT_MODEL,
        timeout_seconds=timeout,
    )


def load_local_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_env_value(value)
    return values


def _strip_env_value(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def sanitize_endpoint(base_url: str | None) -> str:
    if not base_url:
        return "unconfigured"
    parts = urlsplit(base_url)
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    if not host:
        return "configured"
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, host, path, "", "")) if parts.scheme else host


def make_candidate_id(model: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", model.strip()).strip("._-")
    return value or "model_candidate"


def generate_candidates(
    *,
    tasks: list[RFIDAPBenchTaskInfo],
    endpoint: EndpointConfig,
    run_root: Path,
    candidate_root: Path,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> dict[str, GenerationRecord]:
    raw_dir = run_root / "raw_responses"
    extracted_dir = run_root / "extracted_rtl"
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    candidate_root.mkdir(parents=True, exist_ok=True)

    client = OpenAICompatibleClient(
        base_url=endpoint.base_url or "",
        api_key=endpoint.credential or "",
        timeout=endpoint.timeout_seconds,
    )
    records: dict[str, GenerationRecord] = {}
    try:
        for task in tasks:
            try:
                result = client.generate(
                    model=endpoint.model,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=task.prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
            except Exception as exc:  # noqa: BLE001 - report bounded smoke failures per task.
                records[task.task_id] = GenerationRecord(
                    task_id=task.task_id,
                    generation_status="request_failed",
                    extraction_status="not_run",
                    candidate_file_available=False,
                    latency_seconds=None,
                    notes=_safe_report_note(f"generation request failed: {exc}"),
                )
                continue

            (raw_dir / f"{task.task_id}.txt").write_text(result.text, encoding="utf-8")
            rtl = extract_all_rtl_modules(result.text, required_module=task.top_module)
            if rtl is None:
                records[task.task_id] = GenerationRecord(
                    task_id=task.task_id,
                    generation_status="completed",
                    extraction_status="failed",
                    candidate_file_available=False,
                    latency_seconds=result.latency_seconds,
                    notes="no complete required top module extracted",
                )
                continue

            extracted_path = extracted_dir / f"{task.task_id}.sv"
            candidate_path = candidate_root / f"{task.task_id}.sv"
            extracted_path.write_text(rtl, encoding="utf-8")
            candidate_path.write_text(rtl, encoding="utf-8")
            records[task.task_id] = GenerationRecord(
                task_id=task.task_id,
                generation_status="completed",
                extraction_status="passed",
                candidate_file_available=True,
                latency_seconds=result.latency_seconds,
                notes="generation and extraction completed",
            )
    finally:
        client.close()
    return records


def make_no_endpoint_rows(
    tasks: list[RFIDAPBenchTaskInfo],
    endpoint: EndpointConfig,
    prompt_profile: str,
) -> list[ModelSmokeRow]:
    missing = ", ".join(endpoint.missing_labels) or "endpoint"
    return [
        ModelSmokeRow(
            benchmark="rfid_apbench",
            task_id=task.task_id,
            sample_id=1,
            model=endpoint.model,
            prompt_profile=prompt_profile,
            endpoint_status=endpoint.status,
            generation_status="blocked",
            extraction_status="not_run",
            candidate_file_available=False,
            compile_pass=False,
            correctness_pass=False,
            synth_pass=False,
            timing_status="not_required" if not task.timing_required else "unavailable",
            area_metric_available=False,
            activity_metric_available=False,
            reference_area=None,
            generated_area=None,
            area_unit=None,
            reference_activity=None,
            generated_activity=None,
            activity_metric=None,
            area_score=None,
            activity_score=None,
            score=None,
            score_status="invalid",
            failure_category="endpoint_unavailable",
            toolchain_id="unavailable",
            workload_id=str(task.activity_workload.get("workload_id", "unknown_workload")),
            notes=f"model smoke blocked because missing {missing}",
        )
        for task in tasks
    ]


def merge_rows(
    *,
    tasks: list[RFIDAPBenchTaskInfo],
    endpoint: EndpointConfig,
    prompt_profile: str,
    generation_records: dict[str, GenerationRecord],
    evaluation_rows: list[CandidateEvaluationRow],
) -> list[ModelSmokeRow]:
    eval_by_task = {row.task_id: row for row in evaluation_rows}
    rows: list[ModelSmokeRow] = []
    for task in tasks:
        generation = generation_records.get(
            task.task_id,
            GenerationRecord(
                task_id=task.task_id,
                generation_status="not_run",
                extraction_status="not_run",
                candidate_file_available=False,
                latency_seconds=None,
                notes="generation did not produce a candidate",
            ),
        )
        candidate = eval_by_task.get(task.task_id)
        if candidate is None:
            rows.append(_missing_evaluation_row(task, endpoint, prompt_profile, generation))
            continue
        notes = _safe_report_note(generation.notes)
        if candidate.notes and candidate.notes != "candidate validated":
            notes = _safe_report_note(f"{notes}; {candidate.notes}")
        rows.append(
            ModelSmokeRow(
                benchmark="rfid_apbench",
                task_id=task.task_id,
                sample_id=1,
                model=endpoint.model,
                prompt_profile=prompt_profile,
                endpoint_status=endpoint.status,
                generation_status=generation.generation_status,
                extraction_status=generation.extraction_status,
                candidate_file_available=candidate.candidate_file_available,
                compile_pass=candidate.compile_pass,
                correctness_pass=candidate.correctness_pass,
                synth_pass=candidate.synth_pass,
                timing_status=candidate.timing_status,
                area_metric_available=candidate.reference_area is not None and candidate.generated_area is not None,
                activity_metric_available=(
                    candidate.reference_activity is not None and candidate.generated_activity is not None
                ),
                reference_area=candidate.reference_area,
                generated_area=candidate.generated_area,
                area_unit=candidate.area_unit,
                reference_activity=candidate.reference_activity,
                generated_activity=candidate.generated_activity,
                activity_metric=candidate.activity_metric,
                area_score=candidate.area_score,
                activity_score=candidate.activity_score,
                score=candidate.score,
                score_status=candidate.score_status,
                failure_category=candidate.failure_category,
                toolchain_id=candidate.toolchain_id,
                workload_id=candidate.workload_id,
                notes=notes,
            )
        )
    return rows


def write_jsonl_report(rows: list[ModelSmokeRow], output_jsonl: Path) -> None:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.sanitized_dict(), sort_keys=True) + "\n")


def write_csv_report(rows: list[ModelSmokeRow], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.csv_dict())


def write_markdown_report(
    rows: list[ModelSmokeRow],
    output_md: Path,
    *,
    endpoint: EndpointConfig,
    tools: ToolAvailability,
    run_id: str,
) -> None:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    valid_scores = [row.score for row in rows if row.score_status == "valid" and row.score is not None]
    valid_mean = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    all_sample_mean = sum(row.score if row.score_status == "valid" and row.score is not None else 0.0 for row in rows)
    all_sample_mean = all_sample_mean / len(rows) if rows else 0.0
    lines = [
        "# v0.5 RFID-APBench Model Smoke",
        "",
        "## Scope",
        "",
        "This is a bounded model-output smoke for the public/synthetic RFID-APBench area plus activity benchmark.",
        "",
        "- Benchmark: `rfid_apbench`",
        "- Task count: 5",
        "- Samples per task: 1",
        f"- Model: `{endpoint.model}`",
        "- Prompt profile: `neutral_baseline`",
        f"- Run id: `{run_id}`",
        "",
        "## Non-Goals",
        "",
        "- This is not fine-tuning, dataset creation, or adapter training.",
        "- This is not a private RFID evaluation.",
        "- This does not commit raw prompts, raw model responses, generated RTL, VCDs, simulator logs, synthesis logs, compiled artifacts, secrets, model weights, training datasets, or LoRA/QLoRA/DoRA adapters.",
        "",
        "## Model and Endpoint Availability",
        "",
        f"- Endpoint status: `{endpoint.status}`",
        f"- Endpoint: `{endpoint.sanitized_endpoint}`",
        f"- Missing configuration: `{', '.join(endpoint.missing_labels) if endpoint.missing_labels else 'none'}`",
        f"- Icarus Verilog compile: `{_tool_status(tools.iverilog)}`",
        f"- Icarus runtime vvp: `{_tool_status(tools.vvp)}`",
        f"- Yosys synthesis: `{_tool_status(tools.yosys)}`",
        "",
        "## Generation and Gate Counts",
        "",
        f"- Tasks evaluated: {len(rows)}",
        f"- Generation completed: {sum(1 for row in rows if row.generation_status == 'completed')}",
        f"- Extraction passed: {sum(1 for row in rows if row.extraction_status == 'passed')}",
        f"- Candidate file available: {sum(1 for row in rows if row.candidate_file_available)}",
        f"- Compile pass: {sum(1 for row in rows if row.compile_pass)}",
        f"- Correctness pass: {sum(1 for row in rows if row.correctness_pass)}",
        f"- Synthesis pass: {sum(1 for row in rows if row.synth_pass)}",
        f"- Timing pass or not required: {sum(1 for row in rows if row.timing_status in {'pass', 'not_required'})}",
        f"- Area metric available: {sum(1 for row in rows if row.area_metric_available)}",
        f"- Activity metric available: {sum(1 for row in rows if row.activity_metric_available)}",
        "",
        "## Scores",
        "",
        f"- Valid score count: {len(valid_scores)}",
        f"- Mean valid score: {valid_mean:.6f}",
        f"- Mean all-sample score with invalid rows as zero: {all_sample_mean:.6f}",
        "",
        "## Per-Task Sanitized Results",
        "",
        "| task_id | generation | extraction | compile | correctness | synthesis | score_status | score | failure_category | notes |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        data = row.csv_dict()
        lines.append(
            "| "
            + " | ".join(
                [
                    data["task_id"],
                    data["generation_status"],
                    data["extraction_status"],
                    data["compile_pass"],
                    data["correctness_pass"],
                    data["synth_pass"],
                    data["score_status"],
                    data["score"],
                    data["failure_category"],
                    data["notes"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Activity Proxy Caveat",
            "",
            "Activity is a VCD toggle-count proxy from the declared public workload. It is not measured silicon power, signoff power, or final PPA.",
            "",
            "## Artifact Policy",
            "",
            "Raw model responses and extracted/generated RTL are written only to ignored working directories when a model endpoint is available. The committed artifacts are sanitized Markdown, CSV, and JSONL summaries.",
            "",
        ]
    )
    output_md.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run bounded public RFID-APBench model smoke evaluation.")
    parser.add_argument("--benchmark-root", type=Path, default=Path("benchmarks/rfid_apbench"))
    parser.add_argument("--work-dir", type=Path, default=Path(".tmp/rfid_apbench_model_smoke"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/rfid_apbench/model_smoke"))
    parser.add_argument("--output-md", type=Path, default=Path("reports/v0.5_rfid_apbench_model_smoke.md"))
    parser.add_argument("--output-csv", type=Path, default=Path("reports/v0.5_rfid_apbench_model_smoke.csv"))
    parser.add_argument("--output-jsonl", type=Path, default=Path("reports/v0.5_rfid_apbench_model_smoke.jsonl"))
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--prompt-profile", default=DEFAULT_PROMPT_PROFILE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    benchmark_root = args.benchmark_root.resolve()
    endpoint = load_endpoint_config()
    tasks = list(RFIDAPBenchAdapter(benchmark_root).load_task_infos())
    if len(tasks) != 5:
        raise ValueError(f"RFID-APBench model smoke expects 5 tasks, found {len(tasks)}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tools = detect_tools()
    if not endpoint.available:
        rows = make_no_endpoint_rows(tasks, endpoint, args.prompt_profile)
    else:
        candidate_id = make_candidate_id(endpoint.model)
        run_root = (args.output_root / run_id).resolve()
        candidate_root = (args.work_dir / "candidates" / candidate_id).resolve()
        generation_records = generate_candidates(
            tasks=tasks,
            endpoint=endpoint,
            run_root=run_root,
            candidate_root=candidate_root,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
        )
        evaluation_rows = evaluate_candidates(
            benchmark_root=benchmark_root,
            candidate_root=candidate_root,
            work_dir=(args.work_dir / "evaluation").resolve(),
            tools=tools,
        )
        rows = merge_rows(
            tasks=tasks,
            endpoint=endpoint,
            prompt_profile=args.prompt_profile,
            generation_records=generation_records,
            evaluation_rows=evaluation_rows,
        )

    output_md = args.output_md.resolve()
    output_csv = args.output_csv.resolve()
    output_jsonl = args.output_jsonl.resolve()
    write_markdown_report(rows, output_md, endpoint=endpoint, tools=tools, run_id=run_id)
    write_csv_report(rows, output_csv)
    write_jsonl_report(rows, output_jsonl)
    print(f"Wrote {output_md}")
    print(f"Wrote {output_csv}")
    print(f"Wrote {output_jsonl}")
    return 0


def _missing_evaluation_row(
    task: RFIDAPBenchTaskInfo,
    endpoint: EndpointConfig,
    prompt_profile: str,
    generation: GenerationRecord,
) -> ModelSmokeRow:
    return ModelSmokeRow(
        benchmark="rfid_apbench",
        task_id=task.task_id,
        sample_id=1,
        model=endpoint.model,
        prompt_profile=prompt_profile,
        endpoint_status=endpoint.status,
        generation_status=generation.generation_status,
        extraction_status=generation.extraction_status,
        candidate_file_available=generation.candidate_file_available,
        compile_pass=False,
        correctness_pass=False,
        synth_pass=False,
        timing_status="not_required" if not task.timing_required else "unavailable",
        area_metric_available=False,
        activity_metric_available=False,
        reference_area=None,
        generated_area=None,
        area_unit=None,
        reference_activity=None,
        generated_activity=None,
        activity_metric=None,
        area_score=None,
        activity_score=None,
        score=None,
        score_status="invalid",
        failure_category="evaluation_unavailable",
        toolchain_id="unavailable",
        workload_id=str(task.activity_workload.get("workload_id", "unknown_workload")),
        notes=_safe_report_note(generation.notes),
    )


def _first_nonempty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _float_env(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _safe_note(value: str) -> str:
    safe = value.replace("|", "/").replace("\n", " ")
    for marker in ("sk-", "Bearer "):
        if marker in safe:
            safe = safe.replace(marker, "[redacted]-")
    return safe[:160]


def _safe_report_note(value: str) -> str:
    safe = _safe_note(value)
    replacements = {
        "raw_response": "response",
        "raw_responses": "responses",
        "raw_prompt": "prompt_input",
        "outputs/": "artifact_dir/",
        "raw model response": "model response",
        "module ": "rtl_unit ",
        "endmodule": "rtl_unit_end",
    }
    lowered = safe.lower()
    for marker, replacement in replacements.items():
        if marker in lowered:
            safe = re.sub(re.escape(marker), replacement, safe, flags=re.IGNORECASE)
            lowered = safe.lower()
    return safe[:160]


def _tool_status(path: str | None) -> str:
    return "available" if path else "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
