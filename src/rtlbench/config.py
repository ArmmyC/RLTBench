from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rtlbench.prompt_profiles import find_config_file, resolve_prompt_profile


@dataclass(frozen=True)
class RunConfig:
    benchmark_name: str
    benchmark_root: Path
    split: str | None
    model_preset: str | None
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
    evaluator_type: str | None = None
    extra_body: dict[str, Any] = field(default_factory=dict)
    prompt_profile: str | None = None
    system_prompt: str | None = None


def load_config(path: Path, overrides: dict[str, Any] | None = None) -> RunConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    overrides = overrides or {}
    benchmark = data.get("benchmark", {})
    model = data.get("model", {})
    model_preset = overrides.get("model_preset") or model.get("preset")
    preset_model = _load_model_preset(path, str(model_preset)) if model_preset else {}
    generation = data.get("generation", {})
    prompt = data.get("prompt", {})
    evaluation = data.get("evaluation", {})
    run = data.get("run", {})

    def value(name: str, default: Any, *sources: dict[str, Any]) -> Any:
        if overrides.get(name) is not None:
            return overrides[name]
        for source in sources:
            if source.get(name) is not None:
                return source[name]
        return default

    base_url = value("base_url", None, model, preset_model) or os.getenv("OPENAI_BASE_URL") or os.getenv("QWEN_BASE_URL")
    model_name = value("name", None, model, preset_model) or os.getenv("OPENAI_MODEL") or os.getenv("QWEN_MODEL")
    root = value("root", None, benchmark) or os.getenv("BENCHMARK_ROOT")
    if not base_url or not model_name or not root:
        raise ValueError("model base_url/name and benchmark root are required via YAML, CLI, or environment")

    prompt_profile = value("prompt_profile", prompt.get("profile"), prompt)
    system_prompt = resolve_prompt_profile(path, str(prompt_profile)) if prompt_profile else None

    config = RunConfig(
        benchmark_name=str(value("benchmark", benchmark.get("name", "verilogeval"), benchmark)),
        benchmark_root=Path(str(root)).expanduser(),
        split=value("split", None, benchmark),
        model_preset=str(model_preset) if model_preset else None,
        model=str(model_name),
        base_url=str(base_url),
        api_key=str(value("api_key", None, model, preset_model) or os.getenv("OPENAI_API_KEY") or os.getenv("QWEN_API_KEY") or "EMPTY"),
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
        evaluator_type=value("type", None, evaluation),
        extra_body={**dict(preset_model.get("extra_body") or {}), **dict(model.get("extra_body") or {})},
        prompt_profile=str(prompt_profile) if prompt_profile else None,
        system_prompt=system_prompt,
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


def _load_model_preset(config_path: Path, preset: str) -> dict[str, Any]:
    models_path = find_config_file(config_path, "models.yaml")
    if models_path is None:
        expected = config_path.parent / "models.yaml"
        raise FileNotFoundError(f"Model preset {preset!r} requested, but {expected} does not exist")
    data = yaml.safe_load(models_path.read_text(encoding="utf-8")) or {}
    models = data.get("models", data)
    if preset not in models:
        raise ValueError(f"Unknown model preset {preset!r}; available: {', '.join(sorted(models))}")
    return dict(models[preset] or {})
