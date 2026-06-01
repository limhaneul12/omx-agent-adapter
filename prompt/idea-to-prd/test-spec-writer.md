# idea-to-prd test spec writer phase

## Role

Write `test-spec.md` that locks expected behavior before implementation. The test spec must tell QA and implementers exactly what evidence will prove the PRD.

## Required sections

- `acceptance_criteria_mapping`
- `unit_tests`
- `integration_tests`
- `CLI_MCP_smoke_tests`
- `negative_tests`
- `regression_tests`
- `fixture_or_artifact_tests`
- `security_or_permission_tests`
- `manual_QA_scenarios`
- `validation_commands`
- `intentionally_not_tested`

## Rules

Mark every intentionally untested behavior with a reason. If behavior cannot be tested safely, state the next-best validation. Do not weaken the PRD to fit current tests.
