# Handoff and Timeline Rules

Use these rules when handing work to another contributor or starting a scoped work slice in this repository.

## Required handoff content

A handoff must state:

1. where the project currently stands,
2. what was completed,
3. what was verified,
4. what remains to do next,
5. known blockers, constraints, and non-goals.

Do not hand off only a vague instruction such as "continue from here".

## Development timeline path

For cross-contributor handoffs and new work slices, create or update a dated timeline file:

```text
<project_name>/dev_timeline/<YYYY-MM-DD>.md
```

Use the project name as the folder root when the handoff is outside the repository or when the user asks for an HDD/external workspace. If a repo-owned durable timeline already exists, such as `docs/dev_timeline.md`, keep it for repository history, but still honor the dated handoff timeline when the user requests it.

Each timeline entry should include:

- timestamp and short title,
- actor,
- branch,
- status,
- completed work,
- verification evidence,
- next steps,
- blockers and non-goals.

## Branch rule

Before making project changes, create a branch scoped to the feature or concept.

Branch names should be meaningful and reviewable:

```text
feat/llm-wiki-bootstrap
feat/teamwork-typed-transport-hardening
docs/handoff-timeline-routine
fix/cockpit-team-warning-normalization
```

Avoid generic or random names:

```text
misc
update
wip
branch2
new-work
```

Do not group unrelated concepts into one branch merely because they are small.

## PR rule

When the scoped work is complete:

1. update the timeline with final status and verification,
2. run the relevant validation commands,
3. commit the scoped changes,
4. push the branch,
5. open a PR.

Only merge the PR when the user explicitly asked for merge or the repository policy clearly permits it.

## Ordered routine

When both timeline and branch/PR requirements apply, follow this order:

1. prepare or open the correct workspace,
2. create/update `<project_name>/dev_timeline/<YYYY-MM-DD>.md` with starting status and intended work,
3. create a scoped feature/concept branch,
4. perform the work,
5. update the same timeline with completed work, verification, and next steps,
6. push and open a PR.

## External wiki/HDD workspace rule

If the user asks for a separate LLM Wiki or research repository on HDD, prepare it outside the main source repository. Do not mix that wiki workspace into the application repo unless the user explicitly changes the scope.
