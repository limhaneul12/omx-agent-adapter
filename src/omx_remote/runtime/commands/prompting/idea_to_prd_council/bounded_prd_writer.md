# idea-to-prd-council bounded PRD writer

Write a concise implementation-handoff PRD from existing artifacts only.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the PRD artifact content.

Inputs to inspect:
- `02_research/evidence_ledger.md`
- `02_research/gap_research.md`
- `03_council/sufficiency_votes.md`
- `03_council/risk_critique.md`
- existing repo PRD docs if present under `docs/prd/`

Hard limits:
- Do not run new research.
- Do not rewrite the whole repo docs.
- Do not claim implementation/product completion.
- Keep output under 1,500 words.
- Prefer bullets and tables over long prose.

Required sections:
1. Product frame and non-goals.
2. Primary user/jobs.
3. v1 scope.
4. Evidence/source model.
5. Safety and non-advisory boundary.
6. Polite crawling/source-access policy.
7. Frontend/AdminLite scope.
8. Acceptance criteria.
9. Out-of-scope/future work.
