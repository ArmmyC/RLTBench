from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Any, Iterator, TextIO

from rtlbench.adapters.base import BenchmarkAdapter
from rtlbench.types import BenchmarkTask


class VerilogEvalAdapter(BenchmarkAdapter):
    name = "verilogeval"

    def load_tasks(self) -> Iterator[BenchmarkTask]:
        native_root = self._find_native_root()
        if native_root is not None:
            yield from self._load_native_tasks(native_root)
            return

        dataset = self._find_dataset()
        with self._open(dataset) as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row: dict[str, Any] = json.loads(line)
                    prompt = str(row["prompt"])
                    testbench = str(row.get("test") or row.get("testbench") or "")
                    if not testbench:
                        raise ValueError("missing test/testbench")
                    task_id = str(row.get("task_id") or row.get("id") or line_number)
                    yield BenchmarkTask(
                        task_id=task_id,
                        prompt=prompt,
                        testbench=testbench,
                        module_name=_module_name(prompt),
                        metadata={key: value for key, value in row.items() if key not in {"prompt", "test", "testbench"}},
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"Invalid task at {dataset}:{line_number}: {exc}") from exc

    def _load_native_tasks(self, root: Path) -> Iterator[BenchmarkTask]:
        prompts = sorted(root.glob("*_prompt.txt"))
        if not prompts:
            raise FileNotFoundError(f"No *_prompt.txt files found under {root}")
        for prompt_path in prompts:
            task_id = prompt_path.name.removesuffix("_prompt.txt")
            test_path = root / f"{task_id}_test.sv"
            ref_path = root / f"{task_id}_ref.sv"
            missing = [path.name for path in (test_path, ref_path) if not path.is_file()]
            if missing:
                raise FileNotFoundError(f"Task {task_id} is missing: {', '.join(missing)}")
            prompt = prompt_path.read_text(encoding="utf-8")
            yield BenchmarkTask(
                task_id=task_id,
                prompt=prompt,
                testbench=test_path.read_text(encoding="utf-8"),
                module_name=_module_name(prompt),
                support_files={ref_path.name: ref_path.read_text(encoding="utf-8")},
                metadata={"source_format": "verilogeval_v2", "source_dir": str(root)},
            )

    def build_prompt(self, task: BenchmarkTask) -> str:
        interface_note = (
            f"The required top module is `{task.module_name}`. " if task.module_name else ""
        )
        return (
            f"{task.prompt.rstrip()}\n\n"
            f"{interface_note}Do not change the required module name or interface. "
            "Do not include a testbench. Output only the complete synthesizable RTL module."
        )

    def _find_dataset(self) -> Path:
        if self.root.is_file():
            return self.root
        patterns = []
        if self.split:
            patterns.extend([f"*{self.split}*.jsonl", f"*{self.split}*.jsonl.gz"])
        patterns.extend(["*.jsonl", "*.jsonl.gz"])
        for pattern in patterns:
            matches = sorted(self.root.rglob(pattern))
            if matches:
                return matches[0]
        raise FileNotFoundError(
            f"No VerilogEval v2 task directory or JSONL dataset found under {self.root}. "
            "Set benchmark.root to the NVlabs verilog-eval repository, dataset_spec-to-rtl, "
            "or a .jsonl/.jsonl.gz file."
        )

    def _find_native_root(self) -> Path | None:
        if not self.root.is_dir():
            return None
        candidates = []
        if self.split:
            candidates.extend([self.root / self.split, self.root / f"dataset_{self.split}"])
        candidates.extend([self.root, self.root / "dataset_spec-to-rtl"])
        return next((path for path in candidates if path.is_dir() and any(path.glob("*_prompt.txt"))), None)

    @staticmethod
    def _open(path: Path) -> TextIO:
        if path.suffix == ".gz":
            return gzip.open(path, "rt", encoding="utf-8")
        return path.open("r", encoding="utf-8")


def _module_name(prompt: str) -> str | None:
    match = re.search(
        r"\bmodule(?:\s+named)?\s+`?([A-Za-z_$][\w$]*)", prompt, re.IGNORECASE
    )
    return match.group(1) if match else None
