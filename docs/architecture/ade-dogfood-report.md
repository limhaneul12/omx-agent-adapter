# ADE Dogfood Report

## Scope

This report records the 2026-07-28 local macOS dogfood pass for the first useful
ADE. It distinguishes direct evidence from remaining usability limits.

## Launch and Visual Review

The first `uv run comx-agent ade --cwd .` attempt exposed a real environment
failure: the active `uv` Python extension expected Tcl 8.6.16 resources that
were not present in its virtual environment. The repaired launcher now:

1. probes desktop-runtime compatibility,
2. selects a compatible Python 3.13 framework interpreter when necessary,
3. preserves the invoking installation's package paths,
4. and reports an explicit error when no usable Tk runtime exists.

The repaired application launched as a native macOS window. Mouse/menu
navigation opened New Run, and keyboard input preserved a two-line objective.
Visual review then exposed a narrow Attention pane with clipped state text and
an undifferentiated default-Tk hierarchy. The application now uses an
Orca-inspired dark three-pane operating surface with a Workspace rail, central
Run workspace, persistent Attention rail, state metrics, and explicit provider
readiness. Attention remains split into State, Workspace, and Why columns, with
typed state labels instead of inferred activity.

The original synchronous refresh read blocked the Tk event loop long enough to
make buttons appear inert. Workspace projection and Run inspection now execute
outside the Tk thread while results are applied only from scheduled Tk
callbacks. A real macOS interaction smoke measured:

- application construction: `0.4056s`;
- New Run view switch: `0.0002s`;
- Inspect selected call return: `0.0007s`;
- complete Run inspection rendered: `0.4200s`.

The same pass found and repaired multiline objective overlap in the Run table,
runtime enum-value promotion at the Attention presentation boundary, and the
native white `tk.Scrollbar` island. The final text surfaces use an explicit
`tk.Text` plus themed `ttk.Scrollbar` composition.

Reviewed screenshots:

- [multiline New Run](evidence/ade-new-run-multiline.png)
- [real Runs and Attention after the layout repair](evidence/ade-real-runs-attention.png)
- [Run Detail with normalized and native evidence tabs](evidence/ade-run-detail.png)

## Real Provider Evidence

All requests were read-only and produced verified non-empty result Artifacts.

| Operation | Identity | Result evidence |
| --- | --- | --- |
| direct Codex Run | `run-idem-52a3a4532fdfe7d753488e0c` | `result.md`, 2,362 bytes, SHA-256 `f086bf7e1c763a98ef9d213f7d6a6c8017e85dc874e165f8b8faa81b6b988fd0` |
| direct OMX Run | `run-idem-fc36954038eb9d6103a30eee` | `result.md`, 249 bytes, SHA-256 `6e2795d5309027aaf83a946c93c4aa82c4550fbc4d3855d5c933414927d0ef0d` |
| Codex resume | `run-idem-8560f9bd1e5f83f14260ecb7` | reused observed session `019fa79d-686e-7a31-97d1-4206cbcb464e`; verified result SHA-256 `d08da465a93140ecac1a63e7a2650cdcafe266ec098200a1c6e3b1e5f56e3ec9` |
| Codex to OMX handoff | `handoff-idem-9a9714594be62068fc83340b` | target `run-idem-9088bcf4266459db7d452d7d`; source digest preserved; verified target result SHA-256 `07ceb4e28cbccec6ec39b0709ceb51733f707535363f3d081b858421c20dd29d` |

Repeating the handoff with the same idempotency key returned the same handoff
and target Run and left the number of Run directories unchanged.

The ADE reopened over these durable Runs and displayed Codex and OMX completion,
liveness, objectives, and linked Ready For Review Attention items.

## Final ADE-Native Pass

The independent completion audit rejected CLI-created Runs as ADE dogfood. A
second pass therefore used the real `AdeController` and detached worker path
owned by the Tk application. Every completed record below has
`owner_controller_id: human-ade`:

| ADE action | Identity | Result evidence |
| --- | --- | --- |
| Codex Run | `run-idem-f61a977e74f504830e0b3cc7` | 1,733 bytes, SHA-256 `2ccca104f27471855fd688476e7ee8052ef823f1cd382f5174881f1ece54b219` |
| OMX Run | `run-idem-ae48c28886dd6f10c1c230bb` | 1,005 bytes, SHA-256 `0343efa3fa064603009d02906cb5dae8918725327e123b63dd1dbfa27662a340` |
| Codex resume | `run-idem-8e7836a85558c9ab6d2739c2` | reused session `019fa7b6-b182-7ec1-872c-6905d9e1bf2b`; 1,052 bytes, SHA-256 `0015a8b448ac78f1368945216897d3bca341d852738a07ed070f49c381d59661` |
| Codex to OMX handoff | `handoff-idem-a803f7407c609d0b972b85b6` | target `run-idem-5ae14988179ccbc05f2880ed`; source SHA-256 preserved; target SHA-256 `2f07824932c483a93499e5e95c8024d6e53bdc9eb4c01ad92bde524261eb43c7` |

The Tk New Run form was then driven through its real multiline editor, plan
gate, and Start Run action. ADE process `75803` launched detached operation
`ade-operation-20260728T080504324397Z-9a63c4e7` as process `76774`, then closed
while the Run was active. Reopened ADE process `80405` restored selected Run
`run-idem-0c702a745b61599adfda26c2`, showed it in the Run table, and observed
both Run status and liveness as `running`. The detached process therefore
survived a real ADE restart.

That Run later exposed a live operator issue: the configured Alexandria MCP
refresh token was expired and Codex remained active after logging the OAuth
failure. The Run was cancelled through the ADE cancel action, reaching durable
`cancelled` / `finished` state without leaving either native or detached
processes alive. This is recorded as a recovery finding rather than a successful
work result.

The machine-readable evidence snapshot is
[ade-dogfood-final.json](evidence/ade-dogfood-final.json). It also verifies that
the final `events.jsonl` byte counts and SHA-256 values exactly match every
completed Run record.

## Truthfulness Finding

Ambient execution inside an already-owned OMX session reported
`session_pointer_owner_conflict`. A clean subprocess environment proved that
the installed OMX parser and real direct execution are compatible. The ADE now
labels provider execution readiness as `ready`, `observe-only`, or `missing`
instead of treating any readable provider capability as launch readiness.

## Trusted Agent Application Pass

A final pass used the globally installed `comx-agent agent` surface rather than the desktop GUI or direct lifecycle CLI. The Agent path:

1. started one real read-only Codex Run through `agent start-operation`,
2. returned control immediately with a detached operation ID,
3. was polled through `agent operation`,
4. recovered the authoritative Run ID from the operation result,
5. and verified the Run through `status`, `events`, and `artifacts`.

Observed evidence:

- detached operation reached `succeeded`,
- Run semantic status reached `succeeded`,
- process liveness reached `finished`,
- 61 normalized events were readable,
- five existing verified Artifacts were reported,
- the result Artifact was 1,641 bytes,
- and the requested five evidence-backed audit bullets were present.

This proves that a trusted local Agent can operate the ADE without automating Tk widgets and without creating a second Run lifecycle.

The independent audit also found an unrelated untracked local file, `tests/test_alexandria_api_probe_temp.py`, outside the configured `tests/harness` collection root. It performs a localhost Alexandria probe and ends with unconditional `assert False`. The file is not part of the product implementation or passing CI suite. Its removal requires a separately approved destructive workspace action, so this report records it as a local workspace hygiene blocker rather than silently deleting it or treating it as product evidence.

## Remaining Limits

- Terminal integration intentionally opens the native macOS Terminal or an
  explicitly observed tmux target; the ADE does not embed a PTY.
- Codex Agent/Task topology remains unknown because the native output did not
  expose equivalent structured evidence.
- Tk still cannot reproduce Orca's embedded terminal, animation, or browser
  rendering model. The current theme deliberately targets hierarchy, density,
  state semantics, and responsiveness without copying Orca assets or adding a
  new GUI dependency.
- Finder/editor behavior depends on the local macOS applications configured for
  those targets.

These limits preserve the product boundaries and do not create simulated
provider behavior.
