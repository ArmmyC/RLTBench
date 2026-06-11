from rtlbench.extraction import extract_rtl


def test_extracts_tagged_fence() -> None:
    response = "Explanation\n```systemverilog\nmodule top(input logic a, output logic y); assign y=a; endmodule\n```"
    assert extract_rtl(response) == "module top(input logic a, output logic y); assign y=a; endmodule\n"


def test_extracts_unfenced_module() -> None:
    response = "Here is the answer:\nmodule top; // keep this comment\nendmodule\nDone."
    assert extract_rtl(response) == "module top; // keep this comment\nendmodule\n"


def test_returns_none_without_complete_module() -> None:
    assert extract_rtl("assign y = a;") is None

