# Documentation Policy

## What belongs in git

Commit documentation only when it is durable enough to guide future agents, maintainers, or reviewers.

| Category | Commit? | Examples | Notes |
| --- | --- | --- | --- |
| Product definition and current capability status | Yes | `docs/project-operating-lanes-status.md`, top-level `README.md`, `AGENTS.md` | This prevents agents from using stale route/lane definitions. |
| Operating procedures for current surfaces | Yes | `docs/agent-remote-goal-operating-loop.md` | Keep when the procedure affects safe operation, review gates, evidence, or mutation boundaries. |
| Stable operator/agent examples | Yes | `docs/examples/agent-remote-*.md` | Keep concise and backed by parseable JSON blocks or test coverage so examples do not drift silently. |
| Stable engineering rules | Yes | `docs/rules/` | These are repo conventions, not temporary planning notes. |
| Current-code guardrails for future extension | Yes, only if grounded in current code | `docs/future-runtime-readiness.md` | Keep as a guardrail/refusal list, not as an active roadmap. Delete or move to local planning if it becomes speculative. |
| One-off worker notes / review transcripts | Usually no | `docs/reviews/*` | Do not add new tracked one-off review notes unless they capture durable evidence that cannot live in a status doc or test. |
| Local implementation plans and backlog | No by default | `docs/jobs/` | This directory is gitignored. Use it for local planning, task history, and completion ledgers. |
| Runtime artifacts | No | `.omx/`, `.agent-remote/` | Local runtime/control state only unless explicitly requested otherwise. |

## Decision on the three current status docs

| File | Git decision | Reason |
| --- | --- | --- |
| `docs/project-operating-lanes-status.md` | Keep in git | Canonical status index for the six operating lanes and deprecated/misleading surfaces. |
| `docs/agent-remote-goal-operating-loop.md` | Keep in git | Durable operating procedure for agents using Goal/Ralph/Team/Ultrawork safely. |
| `docs/future-runtime-readiness.md` | Keep in git for now | It records current-code guardrails that prevent premature multi-runtime abstraction. It must remain subordinate to the OMX + Codex product definition and should be deleted/moved to `docs/jobs/` if it drifts into speculation. |

## Status labels

Use the same labels across tracked docs and local `docs/jobs/` plans:

| Label | Meaning |
| --- | --- |
| `implemented baseline` | Usable and tested, but still dogfoodable. |
| `partial` | Important pieces exist, but the lane/surface is not end-to-end complete. |
| `planned` | Concept or scaffold exists; no runtime capability claim. |
| `deferred` | Intentionally paused; include the timestamp and reason. |
| `deprecated` | Misleading, obsolete, or scheduled for removal/replacement. |
| `done` | Completed against explicit evidence and no longer active backlog. |

When marking anything `done`, include evidence:

```text
Status: done
Last reviewed: YYYY-MM-DD HH:MM KST
Evidence: tests, CLI smoke, live dogfood, or commit hash
Remaining: none / dogfood-only / follow-up issue
```

When marking anything `deferred`, include why and when:

```text
Status: deferred
Deferred at: YYYY-MM-DD HH:MM KST
Reason: concrete blocker or product decision
Resume when: concrete trigger
```

## `docs/jobs/` policy

`docs/jobs/` is local planning and should stay out of normal commits.

Rules:

1. Every active job folder should have a `0_overview.md`.
2. The `0_overview.md` is the folder source of truth.
3. Numbered slice files can be historical; do not assume they are still active unless the overview says so.
4. Completed folders must say `Status: done` or `Status: implemented baseline` with evidence.
5. Deferred folders must say `Status: deferred` with a timestamp and resume trigger.
6. Stale plans should be marked historical instead of silently edited into new work.
7. Do not force-add `docs/jobs/` unless explicitly requested.

## Pruning rule

Prefer fewer tracked docs. If two tracked docs say the same thing:

1. keep the shorter source-of-truth status doc,
2. keep the operational procedure only if agents need it to act safely,
3. move transient history to `docs/jobs/` or delete it,
4. update links so future agents do not rediscover stale paths.
