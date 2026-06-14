from __future__ import annotations

import html
import json
from typing import Any

from rtlbench.comparison import TABLE_SPECS, format_value


def _best(data: dict[str, Any], table: str, metric: str) -> str:
    row = next((item for item in data["tables"][table] if item["metric"] == metric), None)
    if not row:
        return "N/A"
    values = [(model, value) for model, value in row["values"].items() if isinstance(value, (int, float))]
    return max(values, key=lambda item: item[1])[0] if values else "N/A"


def render_dashboard(comparison: dict[str, Any], failure: dict[str, Any]) -> str:
    models = comparison["models"]
    title_map = {key: title for key, title, _ in TABLE_SPECS}
    table_html: list[str] = []
    for key, rows in comparison["tables"].items():
        headers = "".join(f"<th>{html.escape(model)}</th>" for model in models)
        body = []
        for row in rows:
            values = "".join(f"<td>{html.escape(format_value(row['values'][model], row['metric']))}</td>" for model in models)
            body.append(f"<tr><th>{html.escape(row['label'])}</th>{values}</tr>")
        warning = ""
        if "lint_only" in key:
            warning = '<p class="note">Lint-only, not functional correctness.</p>'
        elif "synthesis_only" in key:
            warning = '<p class="note">Synthesis-only, not behavior-preserving evidence.</p>'
        elif "behavior_preserving" in key:
            warning = '<p class="note">Generic Yosys cells are not final silicon PPA.</p>'
        table_html.append(f'<section><h2>{html.escape(title_map[key])}</h2>{warning}<div class="table-wrap"><table><thead><tr><th>Metric</th>{headers}</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>')
    if failure["rows"]:
        failure_message = f"Per-task rows available: {len(failure['rows'])}. See the generated failure matrix CSV for full details."
    else:
        failure_message = "Per-task failure data is not available for this run. The summary-level baseline is still shown from registered summaries."
    failure_categories = sorted({category for run in comparison["runs"] for category in run["summary"].get("failure_categories", {})})
    summary_counts = []
    for model in models:
        counts = {category: 0 for category in failure_categories}
        for run in comparison["runs"]:
            if run["model"] == model:
                for category, value in run["summary"].get("failure_categories", {}).items():
                    counts[category] += value
        summary_counts.append([model, *[counts[category] for category in failure_categories]])
    failure_headers = "".join(f"<th>{html.escape(category)}</th>" for category in failure_categories)
    failure_rows = "".join(
        "<tr><th>" + html.escape(str(row[0])) + "</th>" + "".join(f"<td>{value}</td>" for value in row[1:]) + "</tr>"
        for row in summary_counts
    )
    analysis = failure.get("analysis", {})
    def items(values: list[str], empty: str = "None detected in available data.") -> str:
        return "<ul>" + "".join(f"<li>{html.escape(value)}</li>" for value in values) + "</ul>" if values else f"<p>{html.escape(empty)}</p>"
    unique_values = [
        f"{task}: {model}"
        for model, tasks in sorted(analysis.get("unique_by_model", {}).items())
        for task in tasks
    ]
    hardest_values = [
        f"{item['task']}: {item['failed_models']}/{item['models_compared']} models failed"
        for item in analysis.get("hardest_tasks", [])[:25]
    ]
    coverage_rows = "".join(
        f"<tr><td>{html.escape(item['benchmark'])}</td><td>{html.escape(item['mode'])}</td><td>{html.escape(item['model'])}</td><td>{html.escape(item['source'])}</td><td>{item['rows']}</td></tr>"
        for item in failure["coverage"]
    )
    per_task_html = ""
    if failure["rows"]:
        per_task_html = f"""<h3>Per-task coverage</h3><div class="table-wrap"><table><thead><tr><th>Benchmark</th><th>Mode</th><th>Model</th><th>Source</th><th>Rows</th></tr></thead><tbody>{coverage_rows}</tbody></table></div>
<div class="analysis-grid"><div><h3>Failed by all models</h3>{items(analysis.get('failed_all', []))}</div><div><h3>Solved by all models</h3>{items(analysis.get('solved_all', []))}</div><div><h3>Unique solves</h3>{items(unique_values)}</div><div><h3>Pass@5 recovered</h3>{items(analysis.get('pass5_recovered', []), 'No recovery detected.')}</div></div>
<h3>Hardest tasks</h3>{items(hardest_values)}"""
    manifests = sorted({run.get("manifest_path") for run in comparison["runs"] if run.get("manifest_path")})
    manifest_links = "".join(f'<li><a href="../{html.escape(path)}">{html.escape(path)}</a></li>' for path in manifests)
    embedded = json.dumps({"comparison": comparison, "failure": failure}, sort_keys=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RTLBench Baseline v0.1</title>
<style>
:root{{--ink:#16253d;--blue:#2e74b5;--pale:#eef4fa;--line:#d8dee8;--muted:#667085;--warn:#fff4e5}}
*{{box-sizing:border-box}} body{{margin:0;font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink);background:#f7f9fc}}
header,main{{max-width:1200px;margin:auto}} header{{padding:48px 24px 24px}} h1{{font-size:clamp(2rem,5vw,3.5rem);margin:0}} h2{{margin-top:0;color:var(--blue)}}
.subtitle{{color:var(--muted);max-width:760px}} main{{padding:0 24px 56px}} .cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:22px 0}}
.card,section{{background:white;border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 6px 22px #172b4d0d}} .card b{{display:block;font-size:1.2rem;margin-top:4px}}
section{{margin:18px 0}} .table-wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;min-width:760px}} th,td{{border-bottom:1px solid var(--line);padding:10px;text-align:right;white-space:nowrap}} th:first-child{{text-align:left}} thead{{background:var(--pale)}}
.note{{background:var(--warn);padding:10px 12px;border-radius:8px}} .analysis-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}} a{{color:var(--blue);overflow-wrap:anywhere}} footer{{color:var(--muted);padding:20px 0}}
@media(max-width:760px){{.cards,.analysis-grid{{grid-template-columns:1fr}} header{{padding-top:28px}} main,header{{padding-left:14px;padding-right:14px}}}}
</style></head><body>
<header><h1>RTLBench Baseline v0.1</h1><p class="subtitle">Five-model public RTL benchmark baseline. Functional simulation, lint-only, synthesis-only, and equivalence evidence are kept separate.</p></header>
<main><div class="cards">
<div class="card">Models<b>{len(models)}</b></div><div class="card">Benchmark families<b>{len(comparison['metadata']['benchmarks'])}</b></div>
<div class="card">Best VerilogEval pass@1<b>{html.escape(_best(comparison,'functional_rtl_generation','functional_pass_rate'))}</b></div>
<div class="card">Best VerilogEval pass@5<b>{html.escape(_best(comparison,'functional_rtl_generation','pass@5'))}</b></div>
<div class="card">Best RTLLM pass@1<b>{html.escape(max(((m, next((r['values'][m] for r in comparison['tables']['functional_rtl_generation'] if r['benchmark']=='rtllm2'), None)) for m in models), key=lambda x: x[1] if isinstance(x[1], (int,float)) else -1)[0])}</b></div>
<div class="card">Best RTL-OPT equivalence<b>{html.escape(_best(comparison,'rtlopt_behavior_preserving_optimization','equivalence_pass_rate'))}</b></div>
<div class="card">Registered runs<b>{len(comparison['runs'])}</b></div></div>
{"".join(table_html)}
<section><h2>Failure Analysis</h2><p>{html.escape(failure_message)}</p><p>Warnings: {len(failure['warnings'])}</p><h3>Registered summary-level failure counts</h3><div class="table-wrap"><table><thead><tr><th>Model</th>{failure_headers}</tr></thead><tbody>{failure_rows}</tbody></table></div>{per_task_html}</section>
<section><h2>Artifacts</h2><ul><li><a href="../reports/baseline_v0.1_public_rtl_benchmarks.md">Comparison Markdown</a></li><li><a href="../reports/baseline_v0.1_public_rtl_benchmarks.json">Comparison JSON</a></li><li><a href="../reports/baseline_v0.1_public_rtl_benchmarks.csv">Comparison CSV</a></li><li><a href="../reports/baseline_v0.1_failure_matrix.md">Baseline v0.1 Failure Matrix</a></li><li><a href="../reports/baseline_v0.2_failure_matrix.md">Baseline v0.2 Failure Matrix</a></li><li><a href="../artifacts/baseline_v0.2/per_task_results.jsonl">Sanitized Per-Task JSONL</a></li><li><a href="../artifacts/baseline_v0.2/per_task_results.csv">Sanitized Per-Task CSV</a></li>{manifest_links}</ul></section>
<footer>Generated from <code>runs/index.yaml</code>. Manual summary fallbacks are explicitly identified in the embedded source data.</footer>
</main><script id="baseline-data" type="application/json">{embedded}</script></body></html>
"""
