import json

from rtlbench.adapters.verilogeval import VerilogEvalAdapter


def test_loads_jsonl_and_builds_prompt(tmp_path) -> None:
    dataset = tmp_path / "test.jsonl"
    dataset.write_text(
        json.dumps({"task_id": "x", "prompt": "module top(input a, output y);", "test": "module tb; endmodule"}) + "\n",
        encoding="utf-8",
    )
    adapter = VerilogEvalAdapter(dataset)
    task = list(adapter.load_tasks())[0]
    assert task.task_id == "x"
    assert task.module_name == "top"
    assert "Do not change" in adapter.build_prompt(task)


def test_loads_native_v2_triplet(tmp_path) -> None:
    (tmp_path / "Prob001_prompt.txt").write_text(
        "Implement a module named TopModule with output one.", encoding="utf-8"
    )
    (tmp_path / "Prob001_test.sv").write_text("module tb; endmodule", encoding="utf-8")
    (tmp_path / "Prob001_ref.sv").write_text("module RefModule; endmodule", encoding="utf-8")

    task = list(VerilogEvalAdapter(tmp_path).load_tasks())[0]
    assert task.task_id == "Prob001"
    assert task.module_name == "TopModule"
    assert task.support_files["Prob001_ref.sv"] == "module RefModule; endmodule"
