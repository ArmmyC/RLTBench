from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from rtlbench.types import BenchmarkTask, EvaluationResult

MISMATCH_RE = re.compile(r"mismatches?\s*[:=]\s*(\d+)", re.IGNORECASE)
FAIL_RE = re.compile(r"\b(fail(?:ed|ure)?|error)\b", re.IGNORECASE)


class IcarusEvaluator:
    def __init__(self, executable: str = "iverilog", timeout: float = 30.0):
        resolved = _find_executable(executable)
        if not resolved:
            raise FileNotFoundError(
                f"{executable!r} was not found. Install Icarus Verilog or set evaluator.executable."
            )
        self.executable = resolved
        self.vvp = _find_executable("vvp")
        if not self.vvp:
            raise FileNotFoundError("'vvp' was not found; install the complete Icarus Verilog package.")
        self.timeout = timeout

    def evaluate(self, task: BenchmarkTask, rtl_path: Path, work_dir: Path) -> EvaluationResult:
        testbench_path = work_dir / "testbench.sv"
        binary_path = work_dir / "simulation.out"
        testbench_path.write_text(task.testbench, encoding="utf-8")
        support_paths = []
        for filename, contents in task.support_files.items():
            support_path = work_dir / Path(filename).name
            support_path.write_text(contents, encoding="utf-8")
            support_paths.append(support_path)
        compile_cmd = [
            self.executable,
            "-g2012",
            "-o",
            str(binary_path),
            str(rtl_path),
            *(str(path) for path in support_paths),
            str(testbench_path),
        ]
        try:
            compiled = subprocess.run(
                compile_cmd, capture_output=True, text=True, timeout=self.timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            return EvaluationResult(False, False, False, "timeout", _timeout_log("compile", exc))
        compile_log = _command_log(compile_cmd, compiled.stdout, compiled.stderr)
        if compiled.returncode != 0:
            return EvaluationResult(False, False, False, "compile_failure", compile_log)

        sim_cmd = [self.vvp, str(binary_path)]
        try:
            simulated = subprocess.run(
                sim_cmd, capture_output=True, text=True, timeout=self.timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            return EvaluationResult(True, False, False, "timeout", compile_log + _timeout_log("simulation", exc))
        sim_log = _command_log(sim_cmd, simulated.stdout, simulated.stderr)
        output = f"{simulated.stdout}\n{simulated.stderr}"
        mismatch_counts = [int(value) for value in MISMATCH_RE.findall(output)]
        semantic_failure = any(value > 0 for value in mismatch_counts)
        if not mismatch_counts and FAIL_RE.search(output):
            semantic_failure = True
        passed = simulated.returncode == 0 and not semantic_failure
        return EvaluationResult(
            True,
            passed,
            passed,
            "passed" if passed else "simulation_failure",
            compile_log + sim_log,
        )


def _command_log(command: list[str], stdout: str, stderr: str) -> str:
    return f"$ {' '.join(command)}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n"


def _timeout_log(stage: str, exc: subprocess.TimeoutExpired) -> str:
    return f"{stage} timed out after {exc.timeout} seconds\nstdout: {exc.stdout or ''}\nstderr: {exc.stderr or ''}\n"


def _find_executable(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    candidate = Path(sys.prefix) / ("Scripts" if sys.platform == "win32" else "bin") / name
    return str(candidate) if candidate.is_file() else None
