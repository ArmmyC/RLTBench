from pathlib import Path

import pytest

from rtlbench.client import OpenAICompatibleClient
from rtlbench.config import RunConfig
from rtlbench.types import GenerationResult
from rtlbench.runner import run_benchmark


def test_mock_model_runs_through_iverilog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset = tmp_path / "tasks.jsonl"
    dataset.write_text(
        '{"task_id":"and_gate","prompt":"module top(input a, input b, output y);",'
        '"test":"module tb; reg a,b; wire y; top dut(a,b,y); initial begin a=1; b=1; #1; '
        'if (y !== 1) $fatal(1, \\"failed\\"); $display(\\"Mismatches: 0\\"); end endmodule"}\n',
        encoding="utf-8",
    )

    def fake_generate(self, **kwargs) -> GenerationResult:
        return GenerationResult("```verilog\nmodule top(input a, input b, output y); assign y = a & b; endmodule\n```", 0.01, {"total_tokens": 12})

    monkeypatch.setattr(OpenAICompatibleClient, "generate", fake_generate)
    config = RunConfig(
        benchmark_name="verilogeval",
        benchmark_root=dataset,
        split=None,
        model="mock-model",
        base_url="http://unused/v1",
        api_key="EMPTY",
        samples_per_task=1,
        temperature=0.2,
        top_p=0.95,
        max_tokens=256,
        request_timeout=5,
        evaluation_timeout=5,
        retries=0,
        workers=1,
        limit=None,
        output_dir=tmp_path / "outputs",
        iverilog="iverilog",
        extra_body={},
    )

    try:
        output = run_benchmark(config)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))

    results = (output / "results.jsonl").read_text(encoding="utf-8")
    assert '"final_pass": true' in results
    assert (output / "summary.json").is_file()
    assert len(list((output / "raw").glob("*.txt"))) == 1
    assert len(list((output / "rtl").glob("*.sv"))) == 1
