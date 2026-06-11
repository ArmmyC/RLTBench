from rtlbench.evaluator import FAIL_RE, MISMATCH_RE


def test_recognizes_nonzero_mismatches() -> None:
    assert [int(value) for value in MISMATCH_RE.findall("Mismatches: 3 in 100 samples")] == [3]


def test_does_not_treat_zero_mismatches_as_failure() -> None:
    output = "Mismatches: 0 in 100 samples"
    assert all(int(value) == 0 for value in MISMATCH_RE.findall(output))
    assert FAIL_RE.search(output) is None

