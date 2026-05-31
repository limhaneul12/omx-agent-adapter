# idea-to-prd-council bounded validation verdict

Write a concise validation verdict from existing artifacts only.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the validation-verdict artifact content.

Required inputs:
- `03_council/sufficiency_votes.md`
- `04_prd/prd.md`
- `04_prd/test_spec.md`
- `04_prd/execution_plan.md`
- `06_ultragoal/ultragoal_brief.md`

Hard limits:
- Do not run new research.
- Do not reread the whole repository.
- Do not claim the implemented product is complete.
- Do not claim live crawler/API/frontend integration unless the artifacts prove it.
- Keep the verdict under 1,200 words.

Approval rule:
- `approved_for_ultragoal: true` means the PRD/test/execution/UltraGoal handoff is ready for a separate implementation run.
- It does **not** mean the product implementation is complete.
- Use `approved_for_ultragoal: false` if the generated artifacts omit the non-advisory boundary, offline validation, polite crawling/source-access policy, frontend/AdminLite scope, source-gap/manual-review model, or exact verification commands.

Required output:

```yaml
approved_for_ultragoal: true|false
approval_agents:
  - validator
  - ultragoal_readiness_judge
blockers:
  - ...
remaining_gaps:
  - ...
exact_next_command: "..."
artifact_evidence:
  prd: "..."
  test_spec: "..."
  execution_plan: "..."
  ultragoal_brief: "..."
```

Then add a short paragraph explaining the decision.
