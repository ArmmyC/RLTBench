from __future__ import annotations

import argparse
from pathlib import Path

from rtlbench.adapters import ADAPTERS
from rtlbench.config import load_config
from rtlbench.runner import run_benchmark


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run RTL generation benchmarks")
    parser.add_argument("--config", type=Path, default=Path("configs/verilogeval.yaml"))
    parser.add_argument("--benchmark", choices=sorted(ADAPTERS))
    parser.add_argument("--benchmark-root", dest="root")
    parser.add_argument("--split")
    parser.add_argument("--model-preset")
    parser.add_argument("--model", dest="name")
    parser.add_argument("--prompt-profile")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples-per-task", type=int)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--request-timeout", type=float)
    parser.add_argument("--evaluation-timeout", type=float)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--output-dir")
    parser.add_argument("--notes", default="")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    overrides = {
        key: value
        for key, value in vars(args).items()
        if key not in {"config", "overwrite", "notes"}
    }
    config = load_config(args.config, overrides)
    output = run_benchmark(config, overwrite=args.overwrite, notes=args.notes)
    print(f"Results written to {output}")


if __name__ == "__main__":
    main()
