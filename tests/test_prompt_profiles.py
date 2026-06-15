from pathlib import Path

import pytest

from rtlbench.cli import build_parser
from rtlbench.config import load_config
from rtlbench.prompt_profiles import DEFAULT_SYSTEM_PROMPT, load_prompt_profiles
from rtlbench.runner import SYSTEM_PROMPT, _serializable_config, _system_prompt


def _write_config_tree(tmp_path: Path, profile: str | None = None) -> Path:
    configs = tmp_path / "configs"
    experiments = configs / "experiments"
    experiments.mkdir(parents=True)
    (configs / "models.yaml").write_text(
        "models:\n  qwen36-27b:\n    name: qwen36-27b\n    api_key: EMPTY\n",
        encoding="utf-8",
    )
    (configs / "prompt_profiles.yaml").write_text(
        "prompt_profiles:\n"
        "  neutral_baseline:\n"
        f"    system_prompt: {DEFAULT_SYSTEM_PROMPT}\n"
        "  strict_rtl_only:\n"
        "    system_prompt: Return synthesizable RTL only.\n",
        encoding="utf-8",
    )
    prompt_block = f"prompt:\n  profile: {profile}\n" if profile else ""
    config = experiments / "smoke.yaml"
    config.write_text(
        "benchmark:\n  name: verilogeval\n  root: tasks.jsonl\n"
        "model:\n  preset: qwen36-27b\n"
        f"{prompt_block}"
        "generation: {}\nevaluation: {}\nrun: {}\n",
        encoding="utf-8",
    )
    return config


def test_loads_prompt_profile_definitions(tmp_path: Path) -> None:
    path = tmp_path / "prompt_profiles.yaml"
    path.write_text("prompt_profiles:\n  code_only:\n    system_prompt: RTL only.\n", encoding="utf-8")

    assert load_prompt_profiles(path) == {"code_only": "RTL only."}


def test_default_prompt_remains_unchanged(tmp_path: Path) -> None:
    config = load_config(_write_config_tree(tmp_path), {"base_url": "http://example/v1"})

    assert SYSTEM_PROMPT == DEFAULT_SYSTEM_PROMPT
    assert config.prompt_profile is None
    assert config.system_prompt is None
    assert _system_prompt(config) == DEFAULT_SYSTEM_PROMPT


def test_cli_override_selects_and_records_prompt_profile(tmp_path: Path) -> None:
    config_path = _write_config_tree(tmp_path)
    args = build_parser().parse_args(
        ["--config", str(config_path), "--base-url", "http://example/v1", "--prompt-profile", "strict_rtl_only"]
    )
    overrides = {key: value for key, value in vars(args).items() if key not in {"config", "overwrite", "notes"}}

    config = load_config(args.config, overrides)
    snapshot = _serializable_config(config)

    assert config.prompt_profile == "strict_rtl_only"
    assert config.system_prompt == "Return synthesizable RTL only."
    assert _system_prompt(config) == "Return synthesizable RTL only."
    assert snapshot["prompt_profile"] == "strict_rtl_only"


def test_config_selects_neutral_baseline(tmp_path: Path) -> None:
    config = load_config(
        _write_config_tree(tmp_path, "neutral_baseline"),
        {"base_url": "http://example/v1"},
    )

    assert config.prompt_profile == "neutral_baseline"
    assert config.system_prompt == DEFAULT_SYSTEM_PROMPT


def test_unknown_prompt_profile_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown prompt profile 'missing'.*neutral_baseline.*strict_rtl_only"):
        load_config(
            _write_config_tree(tmp_path),
            {"base_url": "http://example/v1", "prompt_profile": "missing"},
        )
