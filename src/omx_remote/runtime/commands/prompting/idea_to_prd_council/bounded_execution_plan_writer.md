# idea-to-prd-council bounded execution plan writer

Write a concise implementation plan from existing artifacts only.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the execution-plan artifact content.

Hard limits:
- Do not run new research.
- Do not claim implementation is complete.
- Keep output under 1,200 words.

Required sections:
1. Ordered implementation slices.
2. File/module ownership boundaries.
3. Collaboration lanes and owner roles.
4. Verification per slice.
5. Rollback/stop conditions.
6. Risks and mitigations.
7. Exact next commands.
