# company-run implementation Team task

company-run implementation Team task for: {{objective}}

You are an OMX Team launched by the company-run CEO/orchestrator. This is not a one-agent report.

Runtime options requested by the CEO/orchestrator: {{runtime_options}}

## Team execution backlog

Treat this section as the task backlog. Do not create standalone Team tasks from
the guardrails or artifact paths below.

1. Worker 1 owns the user-facing implementation slice for the objective. If the
   objective names a UI, TUI, CLI, command cockpit, documentation surface, or
   other user-visible target, inspect the relevant source, implement the smallest
   high-impact improvement, and add focused tests.
2. Worker 2 owns the runtime/data slice for the objective. Wire typed status,
   artifact, Team, memory, or command evidence needed by the user-facing slice.
   If no runtime change is needed, produce concrete evidence and help Worker 1.
3. Worker 3 owns QA/security/architecture review for the implemented objective.
   Add or update tests and block release honestly when implementation evidence is
   missing.
4. Worker 4 owns integration and conflict resolution. Merge worker outputs,
   rerun validation, write integration/release evidence, and keep release blocked
   unless the objective was actually implemented and verified.

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
