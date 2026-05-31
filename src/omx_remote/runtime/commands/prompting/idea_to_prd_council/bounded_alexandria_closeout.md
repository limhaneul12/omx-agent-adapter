# idea-to-prd-council bounded Alexandria closeout

Write a concise summary-only closeout note from existing artifacts only.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the closeout artifact content.

Required inputs to inspect:
- `00_intake/idea.md`
- `01_memory/similar_ideas.md`
- `02_research/evidence_ledger.md`
- `03_council/sufficiency_votes.md`
- `04_prd/prd.md`
- `04_prd/test_spec.md`
- `04_prd/execution_plan.md`
- `05_validation/validation_verdict.md`
- `06_ultragoal/ultragoal_brief.md`

Hard limits:
- Do not run new research.
- Do not reread the whole repository.
- Do not call external memory tools directly; write the closeout artifact only.
- Do not store secrets, tokens, credentials, private account data, or raw logs.
- Do not claim the product implementation is complete.
- Keep output under 800 words.

Required sections:
1. Idea summary.
2. Similar-memory summary and reuse warnings.
3. Evidence summary with confidence and known gaps.
4. PRD/test/execution artifact paths.
5. Validation verdict and approval scope.
6. UltraGoal brief path and exact next command.
7. Follow-up blockers and non-goals.
