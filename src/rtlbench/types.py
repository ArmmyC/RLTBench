from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    prompt: str
    testbench: str
    module_name: str | None = None
    support_files: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResult:
    text: str
    latency_seconds: float
    usage: dict[str, Any] | None = None


@dataclass(frozen=True)
class EvaluationResult:
    compile_pass: bool
    sim_pass: bool
    final_pass: bool
    failure_category: str
    log: str


@dataclass
class SampleResult:
    benchmark: str
    task_id: str
    sample_id: int
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    prompt_hash: str
    raw_response_path: str | None = None
    extracted_rtl_path: str | None = None
    compile_pass: bool = False
    sim_pass: bool = False
    final_pass: bool = False
    failure_category: str = "api_failure"
    error_log_path: str | None = None
    latency_seconds: float | None = None
    token_usage: dict[str, Any] | None = None
    generation_extras: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunPaths:
    root: Path
    raw: Path
    rtl: Path
    logs: Path
