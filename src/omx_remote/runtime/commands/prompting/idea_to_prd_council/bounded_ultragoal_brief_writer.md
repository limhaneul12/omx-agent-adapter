# idea-to-prd-council bounded UltraGoal brief writer

Write a concise UltraGoal-ready brief from existing artifacts only.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the UltraGoal brief artifact content.

Hard limits:
- Do not run new research.
- Do not claim implementation is complete.
- Keep output under 1,000 words.

Required sections:
1. Objective.
2. Constraints.
3. Required stories/slices.
4. Acceptance criteria.
5. Verification commands.
6. Explicit launch gates.
7. Non-goals.
