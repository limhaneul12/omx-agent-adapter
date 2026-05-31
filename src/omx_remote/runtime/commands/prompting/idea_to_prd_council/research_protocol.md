# idea-to-prd-council research protocol

Define a bounded research protocol before web collection.

Persistence contract:
- Do not create, modify, or delete files directly.
- Do not run shell commands only to `mkdir`, `touch`, or write artifact files.
- The adapter will persist your final answer through `--output-last-message`.
- Produce only the research-protocol artifact content.

Required sections:
- Research questions and source tiers.
- Search terms and exclusion rules.
- Role-lane outputs for market, competitor, user-problem, technical-feasibility, and source-cartography lanes.
- Sufficiency stop conditions: `continue_research`, `narrow_scope`, `ready_for_prd`, or `block`.
- Claims that must be cited before PRD generation.
