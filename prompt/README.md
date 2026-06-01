# Prompt assets

This directory stores reusable, agent-facing prompt text that would otherwise become long inline strings in production code.

## Required boundary

The top-level `prompt/` directory is intentional and must remain. It is the repository-owned prompt asset root for command recipes, lifecycle orchestration, Goal/Ralph handoffs, Team/subagent handoffs, review lanes, and Alexandria MCP librarian/memory workflows.

## Prompt categories

Prompt files should be one of these explicit categories:

1. **Executable operational prompt** — long-form instructions that an agent can run from directly. These include role, objective, inputs, context recovery, decision gates, output schema, non-goals, failure modes, and acceptance criteria.
2. **Phase prompt** — one executable slice of a larger macro command, such as `company-run` memory recall or research voting.
3. **Maintenance handoff prompt** — adapter-ops prompts that prepare bounded maintenance evidence and may call a concrete MCP tool when execution is explicit.
4. **Template prompt** — reusable CLI/Goal scaffold text loaded from `prompt/`, not embedded in Python.
5. **Compact descriptor** — allowed only for genuinely small one-off fragments. Do not use a tiny descriptor as a substitute for a lifecycle operating prompt.

## Path rule

Use command-scoped, purpose-named Markdown paths:

```text
prompt/<command-or-namespace>/<purpose>.md
```

Examples:

```text
prompt/route-next/route-next-plan.md
prompt/discovery-gate/discovery-gate.md
prompt/research-brief/research-brief-plan.md
prompt/idea-to-prd/idea-to-prd-plan.md
prompt/company-run/company-run-orchestration.md
prompt/company-run/research-council.md
prompt/goal/prd-authoring.md
prompt/adapter-ops/memory-capture/memory-capture.md
```

Nested folders are justified when a namespace or macro command owns multiple prompt assets. Do not keep nested folders merely for appearance.

## Content rules

- Keep placeholders explicit, for example `<task>`, `<cwd>`, `<artifact_path>`, `<goal_id>`.
- Long reusable prompts must live here, not in Python strings.
- Short inline prompt fragments may remain in Python only when they are not standalone operating prompts.
- Every lifecycle prompt should name its stop condition and the command it must not accidentally execute.
- Alexandria MCP usage must name concrete available tool points such as `alexandria_search_vault`, `alexandria_read_note`, `alexandria_get_current_memory_compact`, `alexandria_ask_obsidian_librarian`, and `alexandria_save_note`; if a writable memory tool is unavailable, the prompt must require an explicit unavailable-tool note instead of vague “integrate with Alexandria” wording.
- Tests should verify required prompt files exist when a command depends on them.
