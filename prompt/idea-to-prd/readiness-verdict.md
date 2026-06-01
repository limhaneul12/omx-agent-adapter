# idea-to-prd readiness verdict phase

## Role

Write `readiness-verdict.md`, the final planning decision before any implementation can begin.

## Verdict options

Choose exactly one:

- `ready_for_implementation_kickoff`
- `revise_prd`
- `ask_user`
- `no_build`

## Required sections

- `verdict`
- `rationale`
- `required_artifacts_present`
- `blockers`
- `safe_assumptions`
- `rejected_alternatives`
- `user_choices_if_needed`
- `next_command`

## Rules

Never mark ready if PRD, test spec, or execution brief are missing, shallow, contradictory, or materially ambiguous. Do not start implementation from this phase.
