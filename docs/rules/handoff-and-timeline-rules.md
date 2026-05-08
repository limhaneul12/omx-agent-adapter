# Handoff and Development Timeline Rules

This rule defines the minimum routine for starting work, handing work off, and preserving reviewable progress in this repository.

## Purpose

Agents and contributors should not start implementation from vague chat memory alone.
Every non-trivial work slice should leave behind:

1. a dated progress record,
2. a concept-appropriate branch,
3. explicit verification evidence,
4. and a reviewable PR.

This keeps handoff quality high and prevents "what were we doing?" drift.

## Required Work Order

For normal feature, refactor, docs, and rule work, use this order:

1. update today's `dev_timeline/<YYYY-MM-DD>.md`,
2. create or switch to a branch whose name matches the slice,
3. implement the slice,
4. run verification,
5. open or update a PR,
6. record the result back into today's timeline entry.

Do not skip the first step just because the task feels small if it changes tracked files or is likely to be handed to another worker.

## Timeline Location and Format

Use the repository-root `dev_timeline/` directory.

Path format:

```text
dev_timeline/<YYYY-MM-DD>.md
```

Example:

```text
dev_timeline/2026-05-08.md
```

Each work entry should use this minimum shape:

```md
# YYYY-MM-DD Development Timeline

## HH:MM KST — 작업 제목

- Actor:
- Branch:
- Status: planned | in_progress | completed | blocked
- 지금까지 완료된 것:
- 검증한 것:
- 다음에 해야 할 것:
- blocker / non-goal:
```

Notes:
- append new sections in chronological order for the day,
- keep entries concrete and evidence-bearing,
- record real branch names and actual verification commands/results,
- if the work spans multiple repos, each repo should keep its own `dev_timeline/<date>.md`.

## Branch Naming Rules

Branch names must describe the feature or concept of the slice.

Preferred prefixes:
- `feat/`
- `fix/`
- `refactor/`
- `docs/`
- `test/`
- `ci/`

Good examples:
- `feat/teamwork-typed-transport`
- `docs/llm-wiki-bootstrap`
- `refactor/cockpit-snapshot-normalization`

Avoid vague or person-based names such as:
- `test-branch`
- `work-1`
- `misc-fix`
- `haneul-task`

Branch naming should reflect the repository concept and the actual slice under review.
Do not create disposable branch names that make PR history unreadable.

## Handoff Requirements

When handing work to another contributor or agent, include all of the following:

1. current branch name,
2. current repo path,
3. current scope boundary,
4. what is already complete,
5. what was verified,
6. what remains next,
7. any blockers or explicit non-goals,
8. the PR link if one exists.

A handoff is incomplete if the receiver still has to infer the branch, repo path, or next intended slice from chat history.

## Verification and PR Requirements

Before saying a slice is ready:

1. run the relevant verification commands,
2. record the result in the timeline entry,
3. push the branch,
4. open or update a PR.

For this repository, the default verification expectation is usually:

```text
uv run ruff check src tests
uv run pyrefly check src
uv run pytest -q
```

If a smaller slice intentionally uses a narrower verification set, say so explicitly in the timeline and PR.

## Separate Workspace Rule

When a task belongs to a different project or knowledge base, do not mix it into this repository.
Use a separate workspace/repo instead.

Examples:
- `omx-agent-adapter` work stays here,
- an LLM Wiki or knowledge-base setup should live in its own HDD-backed repo/workspace.

This avoids leaking unrelated artifacts, docs, or experiments into the product repository.

## Historical Note

Older work may still appear in `docs/dev_timeline.md` from before this rule existed.
Treat `dev_timeline/<YYYY-MM-DD>.md` as the forward-looking canonical location for dated progress tracking.
