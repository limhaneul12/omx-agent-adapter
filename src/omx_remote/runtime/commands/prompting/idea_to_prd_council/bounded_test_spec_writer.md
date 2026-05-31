# idea-to-prd-council bounded test spec writer

Write a concise test spec from existing artifacts only.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the test-spec artifact content.

Hard limits:
- Do not run new research.
- Do not claim tests were executed.
- Keep output under 1,200 words.

Required sections:
1. Default offline validation policy.
2. Contract tests.
3. Crawler/source-gap tests.
4. Backend/API boundary tests.
5. Frontend/AdminLite/redaction tests.
6. Non-advisory/trading-affordance checks.
7. Exact commands to run.
8. Release done criteria.
