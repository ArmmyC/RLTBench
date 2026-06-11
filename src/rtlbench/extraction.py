from __future__ import annotations

import re

FENCE_RE = re.compile(
    r"```(?:systemverilog|verilog|sv)?\s*\n?(.*?)```", re.IGNORECASE | re.DOTALL
)
MODULE_RE = re.compile(r"\bmodule\b.*?\bendmodule\b", re.IGNORECASE | re.DOTALL)


def extract_rtl(response: str) -> str | None:
    """Extract the first complete Verilog/SystemVerilog module from a response."""
    if not response or not response.strip():
        return None

    candidates = [match.group(1).strip() for match in FENCE_RE.finditer(response)]
    candidates.append(response.strip())

    for candidate in candidates:
        match = MODULE_RE.search(candidate)
        if match:
            return match.group(0).strip() + "\n"
    return None

