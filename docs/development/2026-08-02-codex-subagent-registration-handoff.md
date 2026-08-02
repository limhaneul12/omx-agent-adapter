# Codex project subagent registration handoff

Date: 2026-08-02

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
- the canonical user home is rejected as a workspace, including symlink aliases;
- `.codex`, `agents`, config, and requested agent-file symlinks are rejected;
- no global `~/.codex` target exists.

`validate` resolves and checks the workspace, existing TOML, and every planned
destination without creating a directory or file. `register` updates requested
`[agents.<name>]` sections, preserves unrelated TOML sections and unrequested
registrations, writes requested agent files atomically, and writes config last.
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
- `src/comx_harness/ade/codex_subagent_toml.py`: deterministic TOML parsing,
  targeted config updates, rendering, and atomic writes.
- `src/comx_harness/ade/codex_subagent_cli.py`: nested Typer JSON commands.
- `examples/codex-subagents/stock-informer.json`: five-agent dogfood spec.
- `tests/harness/ade/test_codex_subagent_registry.py`: schema, filesystem,
  round-trip, update, traversal, and symlink coverage.
- `tests/harness/ade/test_codex_subagent_cli.py`: list/validate/register JSON
  command coverage.

README, the Korean usage guide, and the former stale subagent TOML example now
document only the project-local JSON workflow.

## Verification evidence

- Focused registry and CLI tests:
  `23 passed in 0.24s`.
- `make ruff`:
  `134 files already formatted`; `All checks passed!`.
- `make pyrefly`:
  `0 errors` (Pyrefly also emitted its existing `PYTHONPATH` environment
  warning).
- Broad deterministic suite excluding the two environment-blocked modules:
  `156 passed, 2 deselected in 19.70s`.
- `make native-test`: `2 passed, 163 deselected in 5.55s`.
- `comx-agent agent --help` shows `codex-subagents`.
- `comx-agent agent codex-subagents --help` shows `list`, `validate`, and
  `register`.

`make test` was attempted exactly as requested on the final code. It reached 44%
and the Python
process aborted in the existing Tk startup test while calling the uv-managed
Python 3.13 Tcl/Tk runtime. This was a fatal interpreter abort, not a pytest
assertion failure. A non-Tk retry passed 145 tests before the existing wheel
packaging test failed because `uv build` could not resolve `hatchling` from
PyPI with DNS disabled. Excluding only those two environment-dependent modules
produced the 156-pass result above. An explicit offline wheel build also
confirmed that `hatchling` is not present in the accessible cache.

`make ci` was also attempted. Ruff and Pyrefly passed, then CI stopped at the
same fatal Tk test before reaching its build target. An independent read-only
code review initially found home-target, prospective-validation, strict-integer,
malformed-entry, and write-race gaps. Those were fixed with regression coverage;
the follow-up verdict was `APPROVE` with no remaining blocker in scope.

## Remaining caveats

- Registration state proves project file consistency, not native Codex loading,
  spawn success, scheduling, or topology. Codex structured topology remains
  unknown unless the provider exposes evidence.
- Codex ignores project `.codex/config.toml` for an untrusted project; this
  command does not change trust state.
- Requested registration sections are deterministic replacements. Comments or
  extra keys inside those requested sections are not preserved; unrelated
  sections are preserved.
- Unregistered agent files are reported but never deleted.
- Full `make test`/`make ci` and wheel-build proof remain blocked in this
  sandbox by the Tk interpreter abort and unavailable network/build dependency,
  as detailed above.

No commit or push was performed.
