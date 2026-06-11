from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RunConfig:
    benchmark_name: str
    benchmark_root: Path
    split: str | None
    model: str
    base_url: str
    api_key: str
    samples_per_task: int
    temperature: float
    top_p: float
    max_tokens: int
    request_timeout: float
    evaluation_timeout: float
    retries: int
    workers: int
    limit: int | None
    output_dir: Path
    iverilog: str
    extra_body: dict[str, Any]


def load_config(path: Path, overrides: dict[str, Any] | None = None) -> RunConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    overrides = overrides or {}
    benchmark = data.get("benchmark", {})
    model = data.get("model", {})
    generation = data.get("generation", {})
    evaluation = data.get("evaluation", {})
    run = data.get("run", {})

    def value(name: str, default: Any, *sources: dict[str, Any]) -> Any:
        if overrides.get(name) is not None:
            return overrides[name]
        for source in sources:
            if name in source:
                return source[name]
        return default

    base_url = value("base_url", None, model) or os.getenv("OPENAI_BASE_URL") or os.getenv("QWEN_BASE_URL")
    model_name = value("name", None, model) or os.getenv("OPENAI_MODEL") or os.getenv("QWEN_MODEL")
    root = value("root", None, benchmark) or os.getenv("BENCHMARK_ROOT")
    if not base_url or not model_name or not root:
        raise ValueError("model base_url/name and benchmark root are required via YAML, CLI, or environment")

    config = RunConfig(
        benchmark_name=str(value("benchmark", benchmark.get("name", "verilogeval"), benchmark)),
        benchmark_root=Path(str(root)).expanduser(),
        split=value("split", None, benchmark),
        model=str(model_name),
        base_url=str(base_url),
        api_key=str(value("api_key", None, model) or os.getenv("OPENAI_API_KEY") or os.getenv("QWEN_API_KEY") or "EMPTY"),
        samples_per_task=int(value("samples_per_task", 1, run)),
        temperature=float(value("temperature", 0.2, generation)),
        top_p=float(value("top_p", 0.95, generation)),
        max_tokens=int(value("max_tokens", 2048, generation)),
        request_timeout=float(value("request_timeout", 300, model)),
        evaluation_timeout=float(value("evaluation_timeout", 30, evaluation)),
        retries=int(value("retries", 2, model)),
        workers=int(value("workers", 1, run)),
        limit=_optional_int(value("limit", None, run)),
        output_dir=Path(str(value("output_dir", "outputs", run))).expanduser(),
        iverilog=str(value("executable", "iverilog", evaluation)),
        extra_body=dict(model.get("extra_body") or {}),
    )
    if config.samples_per_task < 1:
        raise ValueError("samples_per_task must be at least 1")
    if config.workers < 1:
        raise ValueError("workers must be at least 1")
    if config.limit is not None and config.limit < 1:
        raise ValueError("limit must be at least 1")
    return config


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)
