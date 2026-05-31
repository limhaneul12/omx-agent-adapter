# idea-to-prd-council gap disposition

Read the already-created research and council artifacts before doing anything else.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the gap disposition artifact content.

Required inputs:
- `02_research/research_protocol.md`
- `02_research/evidence_ledger.md`
- `03_council/evidence_audit.md`
- `03_council/risk_critique.md`
- `03_council/sufficiency_votes.md`

Rules:
- Treat the council sufficiency vote as a stop condition.
- If the overall vote is `ready_for_prd`, write a short gap disposition and proceed without more live web research.
- If the overall vote is `narrow_scope` but the scoped PRD is still viable, write the narrowed scope, blocked/future gaps, and proceed without more live web research.
- If the overall vote is `continue_research` or `block`, do not collect endlessly. Write the exact unresolved gaps, the missing evidence needed, and a blocked/follow-up verdict.
- Separate evidence from inference.
- Prefer local artifact paths and already-cited sources from earlier research artifacts.
- Do not claim a live integration, crawler/API implementation, or runtime launch that has not happened.

Required output sections:
1. Council vote readout.
2. Gaps accepted into PRD scope.
3. Gaps deferred or blocked.
4. Whether more live research is required before PRD generation.
5. Verdict: `ready_for_prd`, `narrow_scope_ready_for_prd`, `continue_research`, or `blocked`.
