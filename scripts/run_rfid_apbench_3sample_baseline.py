from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx


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
from run_rfid_apbench_model_smoke import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_PROMPT_PROFILE,
    SYSTEM_PROMPT,
    EndpointConfig,
    load_endpoint_config,
    make_candidate_id,
    _safe_report_note,
)
from rtlbench.adapters.rfid_apbench import RFIDAPBenchAdapter, RFIDAPBenchTaskInfo  # noqa: E402
from rtlbench.area_activity_scoring import validate_sanitized_record  # noqa: E402
from rtlbench.client import OpenAICompatibleClient  # noqa: E402
from rtlbench.extraction import extract_all_rtl_modules  # noqa: E402


EXPECTED_TASKS = 5
SAMPLES_PER_TASK = 3
REPORT_FIELDS = [
    "benchmark",
    "task_id",
    "sample_id",
    "model",
    "prompt_profile",
    "temperature",
    "top_p",
    "max_tokens",
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
class GenerationRecord:
    task_id: str
    sample_id: int
    generation_status: str
    extraction_status: str
    candidate_file_available: bool
    failure_category: str
    notes: str


@dataclass
class BaselineRow:
    benchmark: str
    task_id: str
    sample_id: int
    model: str
    prompt_profile: str
    temperature: float
    top_p: float
    max_tokens: int
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


def load_tasks(benchmark_root: Path) -> list[RFIDAPBenchTaskInfo]:
    tasks = list(RFIDAPBenchAdapter(benchmark_root).load_task_infos())
    if len(tasks) != EXPECTED_TASKS:
        raise ValueError(f"v0.6 RFID-APBench baseline expects {EXPECTED_TASKS} tasks, found {len(tasks)}")
    return tasks


def tools_available(tools: ToolAvailability) -> bool:
    return tools.healthy_icarus and tools.healthy_yosys


def missing_tool_labels(tools: ToolAvailability) -> tuple[str, ...]:
    missing: list[str] = []
    if tools.iverilog is None:
        missing.append("iverilog")
    if tools.vvp is None:
        missing.append("vvp")
    if tools.yosys is None:
        missing.append("yosys")
    return tuple(missing)


def make_blocker_rows(
    *,
    tasks: list[RFIDAPBenchTaskInfo],
    endpoint: EndpointConfig,
    tools: ToolAvailability,
    samples: int,
    prompt_profile: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    endpoint_status: str | None = None,
    endpoint_unavailable_note: str | None = None,
) -> list[BaselineRow]:
    effective_endpoint_status = endpoint_status or endpoint.status
    if endpoint_unavailable_note is not None:
        failure_category = "endpoint_unavailable"
        notes = endpoint_unavailable_note
    elif not endpoint.available:
        failure_category = "endpoint_unavailable"
        missing = ", ".join(endpoint.missing_labels) or "endpoint"
        notes = f"3-sample baseline blocked because missing {missing}"
    elif missing_tool_labels(tools):
        failure_category = "tool_unavailable"
        missing = ", ".join(missing_tool_labels(tools)) or "EDA tool"
        notes = f"3-sample baseline blocked because missing {missing}"
    else:
        failure_category = "tool_health_failed"
        notes = "3-sample baseline blocked because an EDA tool failed its health check"
    rows: list[BaselineRow] = []
    for sample_id in range(1, samples + 1):
        for task in tasks:
            rows.append(
                BaselineRow(
                    benchmark="rfid_apbench",
                    task_id=task.task_id,
                    sample_id=sample_id,
                    model=endpoint.model,
                    prompt_profile=prompt_profile,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    endpoint_status=effective_endpoint_status,
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
                    failure_category=failure_category,
                    toolchain_id="unavailable",
                    workload_id=str(task.activity_workload.get("workload_id", "unknown_workload")),
                    notes=notes,
                )
            )
    return rows


def endpoint_reachable(endpoint: EndpointConfig) -> bool:
    if not endpoint.available:
        return False
    try:
        with httpx.Client(
            timeout=min(endpoint.timeout_seconds, 10.0),
            headers={"Authorization": f"Bearer {endpoint.credential or ''}"},
        ) as client:
            response = client.get(f"{(endpoint.base_url or '').rstrip('/')}/models")
            response.raise_for_status()
    except httpx.HTTPError:
        return False
    return True


def generate_samples(
    *,
    tasks: list[RFIDAPBenchTaskInfo],
    endpoint: EndpointConfig,
    run_root: Path,
    candidate_root: Path,
    samples: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> dict[tuple[str, int], GenerationRecord]:
    raw_dir = run_root / "raw_responses"
    extracted_dir = run_root / "extracted_rtl"
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    candidate_root.mkdir(parents=True, exist_ok=True)

    records: dict[tuple[str, int], GenerationRecord] = {}
    client = OpenAICompatibleClient(
        base_url=endpoint.base_url or "",
        api_key=endpoint.credential or "",
        timeout=endpoint.timeout_seconds,
    )
    try:
        for sample_id in range(1, samples + 1):
            sample_name = f"sample_{sample_id:02d}"
            sample_candidate_root = candidate_root / sample_name
            sample_candidate_root.mkdir(parents=True, exist_ok=True)
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
                except Exception as exc:  # noqa: BLE001 - report bounded failures per sample.
                    records[(task.task_id, sample_id)] = GenerationRecord(
                        task_id=task.task_id,
                        sample_id=sample_id,
                        generation_status="request_failed",
                        extraction_status="not_run",
                        candidate_file_available=False,
                        failure_category="request_failed",
                        notes=_safe_report_note(f"generation request failed: {exc}"),
                    )
                    continue

                raw_path = raw_dir / f"{task.task_id}_{sample_name}.txt"
                raw_path.write_text(result.text, encoding="utf-8")
                if not result.text.strip():
                    records[(task.task_id, sample_id)] = GenerationRecord(
                        task_id=task.task_id,
                        sample_id=sample_id,
                        generation_status="completed",
                        extraction_status="failed",
                        candidate_file_available=False,
                        failure_category="empty_response",
                        notes="empty response",
                    )
                    continue

                rtl = extract_all_rtl_modules(result.text, required_module=task.top_module)
                if rtl is None:
                    records[(task.task_id, sample_id)] = GenerationRecord(
                        task_id=task.task_id,
                        sample_id=sample_id,
                        generation_status="completed",
                        extraction_status="failed",
                        candidate_file_available=False,
                        failure_category="extraction_failure",
                        notes="no complete required top rtl_unit extracted",
                    )
                    continue

                extracted_path = extracted_dir / f"{task.task_id}_{sample_name}.sv"
                candidate_path = sample_candidate_root / f"{task.task_id}.sv"
                extracted_path.write_text(rtl, encoding="utf-8")
                candidate_path.write_text(rtl, encoding="utf-8")
                records[(task.task_id, sample_id)] = GenerationRecord(
                    task_id=task.task_id,
                    sample_id=sample_id,
                    generation_status="completed",
                    extraction_status="passed",
                    candidate_file_available=True,
                    failure_category="passed",
                    notes="generation and extraction completed",
                )
    finally:
        client.close()
    return records


def evaluate_samples(
    *,
    benchmark_root: Path,
    candidate_root: Path,
    work_dir: Path,
    samples: int,
    tools: ToolAvailability,
) -> dict[tuple[str, int], CandidateEvaluationRow]:
    evaluated: dict[tuple[str, int], CandidateEvaluationRow] = {}
    for sample_id in range(1, samples + 1):
        sample_name = f"sample_{sample_id:02d}"
        rows = evaluate_candidates(
            benchmark_root=benchmark_root,
            candidate_root=candidate_root / sample_name,
            work_dir=work_dir / sample_name,
            tools=tools,
        )
        for row in rows:
            evaluated[(row.task_id, sample_id)] = row
    return evaluated


def merge_rows(
    *,
    tasks: list[RFIDAPBenchTaskInfo],
    endpoint: EndpointConfig,
    prompt_profile: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    samples: int,
    generation_records: dict[tuple[str, int], GenerationRecord],
    evaluation_rows: dict[tuple[str, int], CandidateEvaluationRow],
) -> list[BaselineRow]:
    rows: list[BaselineRow] = []
    for sample_id in range(1, samples + 1):
        for task in tasks:
            generation = generation_records.get(
                (task.task_id, sample_id),
                GenerationRecord(
                    task_id=task.task_id,
                    sample_id=sample_id,
                    generation_status="not_run",
                    extraction_status="not_run",
                    candidate_file_available=False,
                    failure_category="candidate_missing",
                    notes="generation did not produce a candidate",
                ),
            )
            evaluation = evaluation_rows[(task.task_id, sample_id)]
            candidate_available = generation.candidate_file_available and evaluation.candidate_file_available
            if candidate_available:
                failure_category = evaluation.failure_category
            else:
                failure_category = generation.failure_category
            notes = _safe_report_note(generation.notes)
            if candidate_available and evaluation.notes and evaluation.notes != "candidate validated":
                notes = _safe_report_note(f"{notes}; {evaluation.notes}")
            rows.append(
                BaselineRow(
                    benchmark="rfid_apbench",
                    task_id=task.task_id,
                    sample_id=sample_id,
                    model=endpoint.model,
                    prompt_profile=prompt_profile,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    endpoint_status=endpoint.status,
                    generation_status=generation.generation_status,
                    extraction_status=generation.extraction_status,
                    candidate_file_available=candidate_available,
                    compile_pass=evaluation.compile_pass if candidate_available else False,
                    correctness_pass=evaluation.correctness_pass if candidate_available else False,
                    synth_pass=evaluation.synth_pass if candidate_available else False,
                    timing_status=evaluation.timing_status,
                    area_metric_available=(
                        candidate_available
                        and evaluation.reference_area is not None
                        and evaluation.generated_area is not None
                    ),
                    activity_metric_available=(
                        candidate_available
                        and evaluation.reference_activity is not None
                        and evaluation.generated_activity is not None
                    ),
                    reference_area=evaluation.reference_area,
                    generated_area=evaluation.generated_area if candidate_available else None,
                    area_unit=evaluation.area_unit,
                    reference_activity=evaluation.reference_activity,
                    generated_activity=evaluation.generated_activity if candidate_available else None,
                    activity_metric=evaluation.activity_metric,
                    area_score=evaluation.area_score if candidate_available else None,
                    activity_score=evaluation.activity_score if candidate_available else None,
                    score=evaluation.score if candidate_available else None,
                    score_status=evaluation.score_status if candidate_available else "invalid",
                    failure_category=failure_category,
                    toolchain_id=evaluation.toolchain_id,
                    workload_id=evaluation.workload_id,
                    notes=notes,
                )
            )
    return rows


def aggregate_score_value(row: BaselineRow) -> float:
    return row.score if row.score_status == "valid" and row.score is not None else 0.0


def write_jsonl_report(rows: list[BaselineRow], output_jsonl: Path) -> None:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.sanitized_dict(), sort_keys=True) + "\n")


def write_csv_report(rows: list[BaselineRow], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.csv_dict())


def write_markdown_report(
    rows: list[BaselineRow],
    output_md: Path,
    *,
    endpoint: EndpointConfig,
    tools: ToolAvailability,
    run_id: str,
) -> None:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    valid_scores = [row.score for row in rows if row.score_status == "valid" and row.score is not None]
    valid_mean = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    all_sample_mean = sum(aggregate_score_value(row) for row in rows) / len(rows) if rows else 0.0
    failures = Counter(row.failure_category for row in rows)
    task_ids = sorted({row.task_id for row in rows})
    samples_per_task = len({row.sample_id for row in rows}) if rows else 0
    effective_endpoint_status = rows[0].endpoint_status if rows else endpoint.status
    lines = [
        "# v0.6 RFID-APBench 3-Sample Baseline",
        "",
        "## Scope",
        "",
        "This report runs a bounded 3-sample model baseline on the existing five public/synthetic RFID-APBench tasks using unchanged v0.5 benchmark assets.",
        "",
        "- Benchmark: `rfid_apbench`",
        f"- Task count: {len(task_ids)}",
        f"- Samples per task: {samples_per_task}",
        f"- Total sample count: {len(rows)}",
        f"- Model: `{endpoint.model}`",
        f"- Prompt profile: `{DEFAULT_PROMPT_PROFILE}`",
        "- Temperature: `0.0`",
        "- Top-p: `1.0`",
        "- Max tokens: `4096`",
        f"- Run id: `{run_id}`",
        "",
        "## Non-Goals",
        "",
        "- No new tasks, prompts, references, testbenches, extractor changes, evaluator changes, or scoring-policy changes were made.",
        "- No model comparison, prompt tuning, fine-tuning, training data creation, private evaluation, or private benchmark integration was performed.",
        "- No measured power, signoff power, final silicon PPA, or production QoR claim is made.",
        "- Raw model responses, generated RTL, VCDs, logs, compiled artifacts, tool scratch files, secrets, model weights, training datasets, and adapter artifacts are not committed.",
        "",
        "## Model And Tool Availability",
        "",
        f"- Endpoint status: `{effective_endpoint_status}`",
        f"- Endpoint: `{endpoint.sanitized_endpoint}`",
        f"- Missing endpoint configuration: `{', '.join(endpoint.missing_labels) if endpoint.missing_labels else 'none'}`",
        f"- Icarus Verilog compile: `{_tool_status(tools.iverilog, tools.iverilog_healthy)}`",
        f"- Icarus runtime vvp: `{_tool_status(tools.vvp, tools.vvp_healthy)}`",
        f"- Yosys synthesis: `{_tool_status(tools.yosys, tools.yosys_healthy)}`",
        "",
        "## Aggregate Gate Counts",
        "",
        f"- Generation completed: {sum(1 for row in rows if row.generation_status == 'completed')}",
        f"- Extraction passed: {sum(1 for row in rows if row.extraction_status == 'passed')}",
        f"- Candidate file available: {sum(1 for row in rows if row.candidate_file_available)}",
        f"- Compile pass: {sum(1 for row in rows if row.compile_pass)}",
        f"- Correctness pass: {sum(1 for row in rows if row.correctness_pass)}",
        f"- Synthesis pass: {sum(1 for row in rows if row.synth_pass)}",
        f"- Area metric available: {sum(1 for row in rows if row.area_metric_available)}",
        f"- Activity metric available: {sum(1 for row in rows if row.activity_metric_available)}",
        "",
        "## Scores",
        "",
        f"- Valid score count: {len(valid_scores)}",
        f"- Mean valid score: {valid_mean:.6f}",
        f"- Mean all-sample score with invalid rows as zero: {all_sample_mean:.6f}",
        "",
        "## Failure Category Distribution",
        "",
        "| failure_category | count |",
        "| --- | ---: |",
    ]
    for category, count in sorted(failures.items()):
        lines.append(f"| {category} | {count} |")

    lines.extend(
        [
            "",
            "## Per-Task Aggregate Summary",
            "",
            "| task_id | samples | generation_completed | extraction_pass | compile_pass | correctness_pass | synthesis_pass | valid_scores | mean_valid_score | all_sample_mean | failure_categories |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    by_task: dict[str, list[BaselineRow]] = defaultdict(list)
    for row in rows:
        by_task[row.task_id].append(row)
    for task_id in task_ids:
        task_rows = sorted(by_task[task_id], key=lambda row: row.sample_id)
        task_valid = [row.score for row in task_rows if row.score_status == "valid" and row.score is not None]
        task_valid_mean = sum(task_valid) / len(task_valid) if task_valid else None
        task_all_mean = sum(aggregate_score_value(row) for row in task_rows) / len(task_rows)
        task_failures = Counter(row.failure_category for row in task_rows)
        failure_text = ", ".join(f"{name}:{count}" for name, count in sorted(task_failures.items()))
        lines.append(
            "| "
            + " | ".join(
                [
                    task_id,
                    str(len(task_rows)),
                    str(sum(1 for row in task_rows if row.generation_status == "completed")),
                    str(sum(1 for row in task_rows if row.extraction_status == "passed")),
                    str(sum(1 for row in task_rows if row.compile_pass)),
                    str(sum(1 for row in task_rows if row.correctness_pass)),
                    str(sum(1 for row in task_rows if row.synth_pass)),
                    str(len(task_valid)),
                    "" if task_valid_mean is None else f"{task_valid_mean:.6f}",
                    f"{task_all_mean:.6f}",
                    failure_text,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Per-Sample Sanitized Summary",
            "",
            "| task_id | sample_id | generation | extraction | compile | correctness | synthesis | area_metric | activity_metric | score_status | score | failure_category | notes |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in sorted(rows, key=lambda item: (item.task_id, item.sample_id)):
        data = row.csv_dict()
        lines.append(
            "| "
            + " | ".join(
                [
                    data["task_id"],
                    data["sample_id"],
                    data["generation_status"],
                    data["extraction_status"],
                    data["compile_pass"],
                    data["correctness_pass"],
                    data["synth_pass"],
                    data["area_metric_available"],
                    data["activity_metric_available"],
                    data["score_status"],
                    data["score"],
                    data["failure_category"],
                    data["notes"],
                ]
            )
            + " |"
        )

    if valid_scores:
        score_note = f"Valid scores range from {min(valid_scores):.6f} to {max(valid_scores):.6f}."
    else:
        score_note = "No valid scores were produced."
    lines.extend(
        [
            "",
            "## Score Distribution Notes",
            "",
            f"- {score_note}",
            "- Invalid rows are counted as zero in the all-sample mean.",
            "- v0.5 one-sample smoke had 4 valid scores, mean valid score 0.946946, and all-sample zero-filled mean 0.757557.",
            "",
            "## Activity Proxy Caveat",
            "",
            "Activity is a VCD toggle-count proxy from the declared public workload. It is not measured silicon power, signoff power, or final silicon PPA.",
            "",
            "## Public Synthetic Caveat",
            "",
            "This is public synthetic RFID-APBench model evaluation. It is not private evaluation and not fine-tuning.",
            "",
            "## Artifact Policy",
            "",
            "Raw model responses, extracted/generated RTL, VCDs, logs, compiled artifacts, and synthesis scratch are written only under ignored output/work directories. The committed artifacts are sanitized Markdown, CSV, and JSONL summaries.",
            "",
        ]
    )
    output_md.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v0.6 RFID-APBench 3-sample model baseline.")
    parser.add_argument("--benchmark-root", type=Path, default=Path("benchmarks/rfid_apbench"))
    parser.add_argument("--samples-per-task", type=int, default=SAMPLES_PER_TASK)
    parser.add_argument("--work-dir", type=Path, default=Path(".tmp/rfid_apbench_3sample_baseline"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/rfid_apbench/3sample_baseline"))
    parser.add_argument("--output-md", type=Path, default=Path("reports/v0.6_rfid_apbench_3sample_baseline.md"))
    parser.add_argument("--output-csv", type=Path, default=Path("reports/v0.6_rfid_apbench_3sample_baseline.csv"))
    parser.add_argument("--output-jsonl", type=Path, default=Path("reports/v0.6_rfid_apbench_3sample_baseline.jsonl"))
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--prompt-profile", default=DEFAULT_PROMPT_PROFILE)
    parser.add_argument(
        "--require-models-preflight",
        action="store_true",
        help="Require /models to answer before generation; disabled by default for local OpenAI-compatible endpoints.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.samples_per_task != SAMPLES_PER_TASK:
        raise ValueError("v0.6 RFID-APBench baseline is bounded to exactly 3 samples per task")

    benchmark_root = args.benchmark_root.resolve()
    tasks = load_tasks(benchmark_root)
    endpoint = load_endpoint_config()
    tools = detect_tools()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not endpoint.available or not tools_available(tools):
        endpoint_note = None
        endpoint_status = endpoint.status
        rows = make_blocker_rows(
            tasks=tasks,
            endpoint=endpoint,
            tools=tools,
            samples=args.samples_per_task,
            prompt_profile=args.prompt_profile,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            endpoint_status=endpoint_status,
            endpoint_unavailable_note=endpoint_note,
        )
    elif args.require_models_preflight and not endpoint_reachable(endpoint):
        rows = make_blocker_rows(
            tasks=tasks,
            endpoint=endpoint,
            tools=tools,
            samples=args.samples_per_task,
            prompt_profile=args.prompt_profile,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            endpoint_status="unavailable",
            endpoint_unavailable_note=(
                "3-sample baseline blocked because required model listing preflight failed"
            ),
        )
    else:
        candidate_id = make_candidate_id(endpoint.model or DEFAULT_MODEL)
        run_root = (args.output_root / run_id).resolve()
        candidate_root = (args.work_dir / "candidates" / candidate_id).resolve()
        generation_records = generate_samples(
            tasks=tasks,
            endpoint=endpoint,
            run_root=run_root,
            candidate_root=candidate_root,
            samples=args.samples_per_task,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
        )
        evaluation_rows = evaluate_samples(
            benchmark_root=benchmark_root,
            candidate_root=candidate_root,
            work_dir=(args.work_dir / "evaluation").resolve(),
            samples=args.samples_per_task,
            tools=tools,
        )
        rows = merge_rows(
            tasks=tasks,
            endpoint=endpoint,
            prompt_profile=args.prompt_profile,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            samples=args.samples_per_task,
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


def _tool_status(path: str | None, healthy: bool) -> str:
    if path is None:
        return "unavailable"
    return "healthy" if healthy else "health_failed"


if __name__ == "__main__":
    raise SystemExit(main())
