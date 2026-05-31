# idea-to-prd-council research council

Run specialist research lanes as independent read-heavy subagent work, then synthesize.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the current specialist lane artifact content.

Role lanes:
- `market_researcher`: user segments, willingness-to-use, existing workflows.
- `competitor_analyst`: alternatives and differentiation.
- `user_problem_researcher`: concrete pain points and jobs-to-be-done.
- `technical_feasibility_reviewer`: implementation feasibility and integration risk.
- `source_cartographer`: source coverage, freshness, and contradiction map.

Every lane must separate evidence from inference and include URLs or local artifact paths when available. Stop when the council has enough evidence; do not collect endlessly.
