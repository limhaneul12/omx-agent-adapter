# company-run implementation Team task

company-run implementation Team task for: {{objective}}

You are an OMX Team launched by the company-run CEO/orchestrator. This is not a one-agent report.

Runtime options requested by the CEO/orchestrator: {{runtime_options}}

## Team execution backlog

Requested native Team worker count: {{worker_count}}

Treat only the bullet lines in this section as native OMX Team task records.
Each bullet starts with the requested owner marker. Preserve one task per owner;
do not collapse these bullets into a single worker lane.

{{owner_matrix}}

## Guardrails, not standalone tasks

Use separate worker ownership lanes. Each worker may use scoped Codex subagents
only inside its assigned boundary. Do not begin implementation unless PRD, test
spec, execution brief, and executive readiness artifacts exist under
`{{company_root}}`. Keep security, architecture, QA, integration, and release
evidence explicit. If this is a dogfood/readiness run for another repo, avoid
unsafe product mutation; write findings and proof artifacts under `.comx-agent/runs`
or the company-run artifact root. Report blockers honestly instead of pretending
release readiness.

## Artifacts to read before editing

These paths are reference inputs and readiness gates, not task IDs:

```text
{{prd_path}}
{{test_spec_path}}
{{execution_brief_path}}
{{kickoff_path}}
{{dispatch_path}}
```

## Output obligation

Return worker status, files changed if any, subagents used inside each worker boundary, blockers, test evidence, security/architecture/QA review notes, and release-readiness recommendation.
