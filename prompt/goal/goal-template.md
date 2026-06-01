# Codex /goal Prompt Template

Goal:
  <What should be completed, and where should the agent stop?>

Context:
  <Relevant files, directories, current state, prior decisions, and known evidence.>

Constraints:
  <Architecture rules, non-goals, safety boundaries, and testing expectations.>

Done When:
  <Concrete completion criteria, including verification commands and behavior that must not regress.>

Route guide:
  - Goal only: small, clear, single-agent task.
  - Goal → Ralph: unclear scope, PRD/owner planning, or execution structure needed.
  - Goal → Ralph → Team: Ralph can split independent worker ownership for real fanout.
  - Ralph → Team: Ralph-owned team fanout without wrapping it as a Goal route.
  - Ultrawork only: focused deep-work executor by itself.
  - UltraGoal: native OMX durable multi-goal workflow; inspect `comx-agent ultragoal status`.

Verification checklist:
  - Targeted tests pass.
  - Static checks pass.
  - Full test suite passes when code changed.
  - Handoff notes explain what changed, what was verified, and what remains.
