# idea-to-prd-council PRD and validation council

Generate product-slug artifacts only after evidence sufficiency is explicit.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the single artifact requested by the current step.

Required role lanes:
- `prd_writer`: product requirements and user stories.
- `test_designer`: acceptance tests and validation strategy.
- `execution_planner`: implementation slices and rollback points.
- `ultragoal_planner`: UltraGoal-ready brief.
- `validator`: approval or blocker verdict.
- `risk_critic`: unresolved assumptions and safety constraints.

Final validation must write `approved_for_ultragoal: true|false`, approval agents, blockers, remaining research gaps, and the exact next command. UltraGoal readiness is agent-approved from artifacts, not default human approval.
