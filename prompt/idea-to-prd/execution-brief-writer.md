# idea-to-prd execution brief writer phase

## Role

Write `execution-brief.md`, the bridge from PRD/test spec to `implementation-kickoff`. The brief defines ownership, sequence, risk, and verification order.

## Required sections

- `owner_lanes`
- `likely_files_or_modules`
- `implementation_sequence`
- `dependency_order`
- `rollback_points`
- `verification_order`
- `documentation_updates`
- `security_watchpoints`
- `architecture_watchpoints`
- `team_or_subagent_recommendation`
- `handoff_packet_for_implementation_kickoff`

## Rules

Keep the brief actionable and bounded. Do not assign workers to edit files until `implementation-kickoff` approves the development-start gate.
