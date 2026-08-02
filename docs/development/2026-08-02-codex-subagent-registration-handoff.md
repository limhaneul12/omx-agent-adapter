# Codex project subagent registration handoff

Date: 2026-08-02
Blocker-resolution pass: 2026-08-03

## Outcome

The ADE now exposes a typed, project-scoped JSON command surface for Codex
custom-agent registration:

```bash
comx-agent agent codex-subagents list WORKSPACE
comx-agent agent codex-subagents validate WORKSPACE SPEC.json
comx-agent agent codex-subagents register WORKSPACE SPEC.json
```

This is an ADE application service. The exact-nine Run lifecycle is unchanged.
The commands do not invoke Codex, OMX, a Run, or a child agent. Codex continues
to own native subagent selection, spawning, scheduling, and session semantics.

## Implemented contract

`codex-subagent-registration.v1` requires at least one agent. Every agent has a
validated name, description, developer instructions, model, reasoning effort,
and sandbox. The optional `max_concurrent_threads_per_session` accepts 1 through
64.

Safe values and path rules:

- names start with a lowercase letter and contain only lowercase letters,
  digits, `_`, or `-`;
- model ids contain only letters, digits, `.`, `_`, or `-`;
- reasoning effort accepts `low`, `medium`, `high`, `xhigh`, or `max`;
- sandbox accepts only `read-only` or `workspace-write`;
- every generated filename is `.codex/agents/<name>.toml`;
- the canonical user home and user-global `~/.codex` tree are rejected as a
  workspace, including symlink aliases;
- `.codex`, `agents`, config, and requested agent-file symlinks are rejected;
- the ADE-local `max` effort does not expand lifecycle `RunOptions`.

`validate` resolves and checks the workspace, existing TOML, and every planned
destination without creating a directory or file. `register` updates requested
`[agents.<name>]` sections, preserves unrelated TOML sections and unrequested
registrations, writes requested agent files atomically, and writes config last.
The updater interprets keys and table paths with `tomllib`, so quoted requested
agent tables, top-level `agents.max_threads`, and quoted concurrency keys are
accepted and normalized. Unsupported compound shapes fail closed rather than
rewriting unrelated values.
`list` reports registered entries, agent-file contents, the concurrency value,
missing or invalid files, non-deterministic references, unsafe names, symlinks,
legacy concurrency keys, and unregistered `.codex/agents/*.toml` files.
On supported local platforms, directory creation and replacement are anchored to
verified directory descriptors with no-follow semantics; unsupported platforms
fail closed instead of falling back to a path-following write.

The implementation follows the Codex project-config contract: custom roles are
declared under `[agents.<name>]`, `config_file` is relative to the declaring
`.codex/config.toml`, and project config is loaded only for trusted projects.
See the [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml).

## Main files

- `src/comx_harness/schemas/codex_subagent_schemas.py`: strict input and JSON
  output contracts.
- `src/comx_harness/ade/codex_subagent_registry.py`: three-operation typed ADE
  service (`list`, `validate`, `register`) and path containment.
- `src/comx_harness/ade/codex_subagent_config.py`: semantic targeted updates of
  existing project config while retaining unrelated TOML text.
- `src/comx_harness/ade/codex_subagent_toml.py`: deterministic agent-file
  rendering plus directory-descriptor-anchored atomic writes.
- `src/comx_harness/ade/codex_subagent_cli.py`: nested Typer JSON commands.
- `examples/codex-subagents/stock-informer.json`: five-agent dogfood spec.
- `tests/harness/ade/test_codex_subagent_registry.py`: schema, filesystem,
  round-trip, update, traversal, and symlink coverage.
- `tests/harness/ade/test_codex_subagent_cli.py`: list/validate/register JSON
  command coverage.

README, the Korean usage guide, and the former stale subagent TOML example now
document only the project-local JSON workflow.

## Resolved Mission blockers

The resumed Mission consumed
`.comx-agent/v2/mission-artifacts/omx-codex-subagent-registration-20260802-001/blockers.json`
and resolved all three verified findings:

1. Registry and CLI regression tests now reject direct or symlink-aliased
   user-global `~/.codex` Workspaces before any project destination is planned.
2. Config updates use parsed TOML paths rather than fixed unquoted regex shapes;
   regressions cover quoted agent tables, `agents.max_threads`, quoted canonical
   concurrency keys, and existing inline agent registration.
3. Shared lifecycle `ReasoningEffort` is unchanged at `low`, `medium`, `high`,
   and `xhigh`; the ADE spec owns a local literal that also permits `max`.
   A regression test proves `RunOptions(reasoning_effort="max")` remains invalid.

## Verification evidence

- Focused registry and CLI tests:
  `30 passed`.
- `make ruff`:
  `135 files already formatted`; `All checks passed!`.
- `make pyrefly`:
  `0 errors` (Pyrefly also emitted its existing `PYTHONPATH` environment
  warning).
- Broad deterministic suite excluding the two environment-blocked modules:
  `163 passed, 2 deselected in 20.76s`.
- `make native-test`: `2 passed, 170 deselected in 4.02s`.
- `comx-agent agent --help` shows `codex-subagents`.
- `comx-agent agent codex-subagents --help` shows `list`, `validate`, and
  `register`.

`make test` was attempted exactly as requested on the blocker-resolved code. It
reached 42%
and the Python
process aborted in the existing Tk startup test while calling the uv-managed
Python 3.13 Tcl/Tk runtime. This was a fatal interpreter abort, not a pytest
assertion failure. Excluding only that Tk module and the distribution packaging
module produced the 163-pass result above. A focused packaging rerun failed
because `uv build` could not fetch `hatchling>=1.27,<2.0` after three DNS
retries.

`make ci` was also attempted after the blocker fixes. Ruff and Pyrefly passed,
then CI stopped at the same fatal Tk test before reaching its build target.
An independent read-only verifier returned `PASS`: all three recorded blockers
are resolved, exact-nine lifecycle and shared execution-contract files remain
unchanged, and no remaining blocker was reproduced.

## Remaining caveats

- Registration state proves project file consistency, not native Codex loading,
  spawn success, scheduling, or topology. Codex structured topology remains
  unknown unless the provider exposes evidence.
- Codex ignores project `.codex/config.toml` for an untrusted project; this
  command does not change trust state.
- Requested registration sections are deterministic replacements. Comments or
  extra keys inside those requested sections are not preserved; unrelated
  sections are preserved.
- Compound inline TOML values that mix a requested registration or concurrency
  setting with unrelated values on the same statement fail closed because the
  updater cannot safely replace only part of that statement.
- Unregistered agent files are reported but never deleted.
- Full `make test`/`make ci` and wheel-build proof remain blocked in this
  sandbox by the Tk interpreter abort and unavailable network/build dependency,
  as detailed above.

No commit or push command was run by this blocker-resolution session. During
verification, an external process advanced this worktree from `2d93f37` to
local commit `4f3a2cf` (`feat: add codex subagent registry commands`) despite
the Mission's no-commit constraint. A mixed reset back to
`2d93f37` was attempted to preserve every file as uncommitted work, but the
linked-worktree Git metadata is read-only in this sandbox and rejected creation
of `index.lock`. The four follow-up blocker-resolution edits remain uncommitted;
no push occurred, and `origin/main` remains at `2d93f37` in the available local
remote-tracking evidence.
