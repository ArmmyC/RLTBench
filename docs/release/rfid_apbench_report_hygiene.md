# RFID-APBench Report Hygiene

Use this guide when creating or reviewing committed RFID-APBench reports. It defines naming, section, schema, lineage, caveat, and artifact-exclusion expectations for public/synthetic RFID-APBench evidence.

This guide is documentation only. It does not change benchmark tasks, prompts, references, testbenches, workloads, metrics, scoring, evaluator policy, prompt profiles, model settings, or token limits.

## Filename Conventions

Use stable, versioned filenames under `reports/`.

Preferred pattern:

```text
reports/v<major>.<minor>_rfid_apbench_<scope>[_<artifact>].md
reports/v<major>.<minor>_rfid_apbench_<scope>.csv
reports/v<major>.<minor>_rfid_apbench_<scope>.jsonl
```

Guidance:

- Use `rfid_apbench` exactly for the benchmark name.
- Use a short lowercase scope, separated by underscores.
- Include the task ID for single-task reports when helpful, such as `ap001_post_clarity_targeted_validation`.
- Use matching stems for Markdown, CSV, and JSONL from the same per-sample run.
- Use Markdown-only reports for planning, closeout, checklist, documentation, and sanitized failure-analysis artifacts that do not emit per-sample rows.
- Do not encode private endpoint names, private paths, secrets, raw-output locations, or model-hosting details in filenames.

Examples:

- `reports/v0.7_rfid_apbench_post_fix_expanded_10task_baseline.md`
- `reports/v0.7_rfid_apbench_post_fix_expanded_10task_baseline.csv`
- `reports/v0.7_rfid_apbench_post_fix_expanded_10task_baseline.jsonl`
- `reports/v0.7_rfid_apbench_post_fix_failure_analysis.md`
- `reports/v0.8_rfid_apbench_report_hygiene.md`

## Required Markdown Sections By Report Type

### Baseline Reports

Baseline reports cover one or more tasks with per-sample generation and evaluation rows.

Required sections:

- title with version, benchmark, and scope
- scope and non-goals
- source evidence used
- run configuration
- endpoint and tool status without secrets
- fixed runner or model-preset behavior when relevant
- manifest/task confirmation
- request outcome distribution
- content/token metadata summary when available
- empty/null-content/token-limit recurrence summary when relevant
- extraction and evaluation gate summary
- per-task aggregate summary for multi-task baselines
- score summary
- comparison against prior evidence only when methodologically valid and clearly bounded
- interpretation
- benchmark asset decision
- fine-tuning readiness decision
- exactly one recommended next bounded direction when the report is part of a decision chain
- activity proxy caveat
- public synthetic/no-private/not-fine-tuning caveat

### Targeted Validation Reports

Targeted validation reports cover a bounded task subset or specific validation question.

Required sections:

- title with version, benchmark, task/scope, and validation type
- scope and non-goals
- source evidence used
- validation configuration
- confirmation of task prompt/asset state when relevant
- confirmation of runner path or model preset behavior when relevant
- request outcome distribution
- per-sample sanitized metadata
- extraction and evaluation gate summary
- correctness result summary
- score summary when any rows pass
- comparison against the specific prior evidence being validated
- interpretation
- benchmark asset decision
- fine-tuning readiness decision
- exactly one recommended next bounded direction when applicable
- activity proxy caveat
- public synthetic/no-private/not-fine-tuning caveat

### Failure Analysis Reports

Failure analysis reports classify invalid rows without exposing raw generated artifacts.

Required sections:

- title with version, benchmark, and failure-analysis scope
- scope and non-goals
- source evidence used
- baseline or validation summary that produced the failure
- affected task/row summary
- public expected behavior at a high level
- sanitized failure taxonomy
- compile/simulation/synthesis classification as applicable
- defect support assessment
- benchmark asset decision
- fine-tuning readiness decision
- exactly one recommended next bounded direction when applicable
- activity proxy caveat
- public synthetic/no-private/not-fine-tuning caveat

### Release Closeout Reports

Release closeouts summarize a release evidence set and release readiness.

Required sections:

- title with version, benchmark, and closeout scope
- scope and non-goals
- source evidence used
- release timeline or evidence sequence
- benchmark inventory
- final validation configuration
- response-boundary or reliability status when relevant
- baseline result summary
- comparison against prior release evidence when useful
- known limitations
- asset and policy decisions
- release readiness
- suggested tag name or tag commands as examples only
- exactly one recommended next bounded direction
- activity proxy caveat
- public synthetic/no-private/not-fine-tuning caveat

### Planning And Documentation Reports

Planning reports include hardening plans, checklist reports, reproducibility docs reports, and hygiene reports.

Required sections:

- title with version, benchmark, and planning/documentation scope
- scope and non-goals
- source evidence used
- artifact or plan summary
- sections or workstreams covered
- how to use the new documentation with existing release evidence
- benchmark asset decision
- fine-tuning readiness decision
- exactly one recommended next bounded direction unless the decision option is explicitly `no_immediate_followup_beyond_documentation`
- activity proxy caveat
- public synthetic/no-private/not-fine-tuning caveat

## When CSV/JSONL Is Required

CSV and JSONL are required when a report is produced from per-sample generation or evaluation rows, including:

- full baselines
- targeted validations
- model-smoke runs
- candidate-evaluation runs

Use the same filename stem as the Markdown report.

CSV/JSONL are not required for:

- planning reports
- release checklist reports
- reproducibility documentation reports
- report hygiene reports
- release closeouts that summarize already committed row artifacts
- sanitized failure analyses that classify existing rows without producing new per-sample rows
- prompt-clarity or policy reports that do not run or evaluate samples

When no CSV/JSONL is required, the Markdown report must say what existing row artifacts or source reports were used.

## Per-Sample CSV/JSONL Schema

For model-generation baselines and targeted validations, required row fields are:

- `benchmark`
- `task_id`
- `sample_id`
- `model`
- `prompt_profile`
- `temperature`
- `top_p`
- `max_tokens`
- `endpoint_status`
- `request_outcome`
- `request_attempt_count`
- `latency_seconds`
- `response_choice_count`
- `response_content_present`
- `response_character_count`
- `finish_reason`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `http_status_class`
- `response_parse_status`
- `generation_status`
- `extraction_status`
- `candidate_file_available`
- `compile_pass`
- `correctness_pass`
- `synth_pass`
- `timing_status`
- `area_metric_available`
- `activity_metric_available`
- `reference_area`
- `generated_area`
- `area_unit`
- `reference_activity`
- `generated_activity`
- `activity_metric`
- `area_score`
- `activity_score`
- `score`
- `score_status`
- `failure_category`
- `toolchain_id`
- `workload_id`
- `notes`

For candidate-fixture evaluation rows, required row fields are:

- `task_id`
- `candidate_id`
- `final_pass`
- `candidate_file_available`
- `compile_pass`
- `correctness_pass`
- `synth_pass`
- `timing_status`
- `reference_area`
- `generated_area`
- `area_unit`
- `reference_activity`
- `generated_activity`
- `activity_metric`
- `area_score`
- `activity_score`
- `score`
- `score_status`
- `failure_category`
- `toolchain_id`
- `workload_id`
- `notes`

Optional fields may be added only when they are sanitized, stable, documented in the report, and do not expose raw prompts, raw responses, generated RTL, logs, private paths, or secrets.

## Allowed Sanitized Endpoint, Request, And Token Metadata

Allowed endpoint metadata:

- endpoint status such as `available`, `unavailable`, or blocker status
- endpoint base URL with credentials removed
- missing configuration labels without secret values
- model name or served model alias

Allowed request and response metadata:

- request outcome
- request attempt count
- latency in seconds
- response choice count
- response content present as a boolean
- response character count
- finish reason
- HTTP status class such as `2xx`, `4xx`, or `5xx`
- response parse status

Allowed token metadata:

- prompt tokens
- completion tokens
- total tokens
- observed token ranges
- explicit note when token counts are unavailable

Never include API keys, authorization headers, raw request bodies, raw response bodies, raw prompts beyond public benchmark prompt text, private endpoint credentials, or private absolute paths.

## Required Gate Fields

Reports and row artifacts must distinguish gates clearly:

- generation completed or blocked
- extraction pass/fail
- candidate file availability
- compile pass/fail
- functional simulation/correctness pass/fail
- synthesis pass/fail
- timing status when relevant
- area metric availability
- activity metric availability
- score validity
- final failure category

Functional simulation is the correctness gate for RFID-APBench tasks. Compile-only or synthesis-only success must not be described as behavioral correctness.

## Score Fields And Aggregation

Required score summaries when rows produce scores:

- valid score count
- mean valid score
- all-sample zero-filled score
- valid score range when useful
- per-task mean valid score for multi-task reports
- per-task all-sample score for multi-task reports

Required score row fields:

- `reference_area`
- `generated_area`
- `area_unit`
- `reference_activity`
- `generated_activity`
- `activity_metric`
- `area_score`
- `activity_score`
- `score`
- `score_status`

Invalid rows must be counted as zero in all-sample zero-filled means. Valid-score means must include only rows with `score_status == "valid"` and a numeric `score`.

Area and activity scores are benchmark metrics from the unchanged evaluator. They are not measured power, signoff power, final silicon PPA, or production QoR.

## Failure Category Guidance

Use the most specific supported failure category. Common categories include:

- `passed`
- `endpoint_unavailable`
- `tool_unavailable`
- `tool_health_failed`
- `tool_startup_failure`
- `request_failed`
- `empty_response`
- `extraction_failure`
- `candidate_missing`
- `compile_failure`
- `simulation_failure`
- `synthesis_failure`
- `timing_failure`
- `area_metric_unavailable`
- `activity_metric_unavailable`
- `activity_failure`
- `reference_metrics_unavailable`

Failure-analysis reports may add sanitized explanatory categories such as:

- `syntax_or_compile_construct_error`
- `incomplete_or_malformed_candidate`
- `edge_filter_semantics_mismatch`
- `wakeup_pulse_width_mismatch`
- `state_update_timing_mismatch`
- `benchmark_asset_issue_not_supported`
- `extractor_issue_not_supported`
- `tool_or_synthesis_issue_not_supported`

Do not invent a benchmark defect, endpoint defect, tool defect, prompt defect, or model-quality conclusion unless the cited evidence supports it. If evidence is insufficient, say so explicitly.

## Source Evidence And Lineage

Every committed Markdown report must include source evidence.

Source evidence should list:

- the governing spec
- prior reports used
- manifest or benchmark docs used
- configs used
- scripts used
- tests or validation evidence used
- CSV/JSONL row artifacts used when applicable

Lineage guidance:

- State whether a report is a new run, targeted validation, failure analysis, closeout, or planning artifact.
- If comparing against prior evidence, name the prior report and explain differences in runner state, prompt state, task set, model, settings, or evaluator.
- Do not compare models unless task set, prompt template, generation settings, and evaluation mode match.
- Do not treat different benchmark states as a pure model-quality comparison.

## Caveats And Claim Safety

Required caveats:

- Activity is a VCD toggle-count proxy from the declared public workload.
- Activity is not measured silicon power, signoff power, final silicon PPA, or production QoR.
- RFID-APBench evidence is public/synthetic.
- Reports contain no private data or private RTL.
- Reports are not private evaluation.
- Reports do not create training data.
- Reports are not fine-tuning readiness evidence.

Required claim-safety rules:

- Do not claim measured power.
- Do not claim final silicon PPA.
- Do not claim model superiority without matched model-comparison evidence.
- Do not claim fine-tuning readiness from public/synthetic evaluation rows.
- Do not claim benchmark asset defects without concrete asset evidence.
- Do not count compile-only or synthesis-only results as functional correctness.

## Benchmark Asset And Fine-Tuning Decisions

Every report must state the benchmark asset decision:

- unchanged assets, or
- explicitly approved asset change and its scope.

Every report must state the fine-tuning readiness decision. The default for v0.7/v0.8 RFID-APBench public/synthetic evidence is:

- fine-tuning remains out of scope and is not recommended.

Do not create training data, fine-tune, add adapters, or add private benchmarks from report-hygiene work.

## Prohibited Raw And Private Artifact Checklist

Before committing, confirm no staged file contains:

- private RTL
- private task text
- raw prompts beyond public benchmark prompt text
- raw model responses
- response bodies
- generated model RTL
- raw benchmark output directories
- VCD files or VCD snippets
- simulator logs
- synthesis logs
- compiled artifacts
- tool scratch files
- endpoint credentials or secrets
- private absolute paths
- model weights
- training datasets
- LoRA, QLoRA, DoRA, or other adapters
- fine-tuning scripts

Ignored locations such as `outputs/`, `.tmp/`, `.env`, caches, logs, and external benchmark checkouts must remain outside committed evidence unless a separate approved spec says otherwise.

## Example Review Checklist For New Reports

- [ ] Filename follows `vX.Y_rfid_apbench_<scope>` convention.
- [ ] Markdown report has scope and non-goals.
- [ ] Source evidence and lineage are listed.
- [ ] Report type has all required sections.
- [ ] CSV/JSONL exists when per-sample rows were produced.
- [ ] CSV/JSONL fields match the expected schema or documented sanitized extension.
- [ ] Endpoint and request metadata are sanitized.
- [ ] Token metadata is summarized without raw responses.
- [ ] Gate counts distinguish extraction, compile, functional simulation, synthesis, area, activity, and scoring.
- [ ] Functional correctness is not inferred from compile or synthesis alone.
- [ ] Score summaries include valid count, mean valid score, and all-sample zero-filled score when scores exist.
- [ ] Invalid-row zero-fill behavior is stated.
- [ ] Failure categories are specific and evidence-backed.
- [ ] Known limitations are documented without overclaiming.
- [ ] Benchmark asset decision is stated.
- [ ] Fine-tuning readiness decision is stated.
- [ ] Activity proxy and public synthetic caveats are present.
- [ ] No measured-power, final-PPA, private-evaluation, model-superiority, or fine-tuning-readiness claims are unsupported.
- [ ] No prohibited raw/private artifact is staged.
- [ ] `python -m pytest` passes.
