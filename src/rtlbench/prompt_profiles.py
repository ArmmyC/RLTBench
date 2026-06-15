from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_SYSTEM_PROMPT = (
    "You are an expert RTL designer. Generate correct, synthesizable Verilog/SystemVerilog "
    "code that satisfies the given specification. Return only the final code unless explanation "
    "is explicitly requested."
)


def load_prompt_profiles(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles = data.get("prompt_profiles", data)
    if not isinstance(profiles, dict):
        raise ValueError(f"Prompt profiles in {path} must be a mapping")

    loaded: dict[str, str] = {}
    for name, entry in profiles.items():
        value: Any = entry
        if isinstance(entry, dict):
            value = entry.get("system_prompt")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Prompt profile {name!r} in {path} must define a non-empty system_prompt")
        loaded[str(name)] = value.strip()
    return loaded


def resolve_prompt_profile(config_path: Path, profile: str) -> str:
    profiles_path = find_config_file(config_path, "prompt_profiles.yaml")
    if profiles_path is None:
        expected = config_path.parent / "prompt_profiles.yaml"
        raise FileNotFoundError(f"Prompt profile {profile!r} requested, but {expected} does not exist")
    profiles = load_prompt_profiles(profiles_path)
    if profile not in profiles:
        available = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown prompt profile {profile!r}; available: {available}")
    return profiles[profile]


def find_config_file(config_path: Path, filename: str) -> Path | None:
    for directory in (config_path.parent, config_path.parent.parent):
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None
