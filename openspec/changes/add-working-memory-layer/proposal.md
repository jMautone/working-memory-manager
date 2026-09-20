## Why

Agent-assisted development multiplies the work a person can have in flight;
it does not multiply their ability to remember where each thread stopped.
That state lives in three fragile places — the person's head, open terminals,
and chat history — and none of them answers "where was I and what's next?"
This change introduces a working memory layer so that interrupting and
resuming an initiative costs under 30 seconds without rereading conversations.

This is Phase 1 ("SWITCH") of the plan in `persistent-working-memory-plan.md`.
Its exit test is a one-week simulation with three real initiatives; the
answers to that test define the scope of later phases, not this document.

## What Changes

- New `wcm` CLI (Python 3.14, invoked as `python -m wcm`) covering the three
  core operations: `pause`, `resume`, `now`
- The supporting Phase 1 commands the core operations need in order to be
  usable in the exit test: `new`, `list`, `show`, `wait`, `done`, `checkpoint`,
  `capture`, `inbox`, `promote`, `edit`
- Storage in `~/.wcm`: one Markdown + YAML frontmatter file per initiative,
  outside any code repository
- Four states (active/paused/waiting/done) with at most one active initiative
- Switch as the primitive operation; `pause` is a switch to nothing
- A five-field NOW block (Focus, Stopped at, Why it matters, Important, Next),
  rewritten on every pause, never grown as a timeline
- Append-only checkpoints capturing what Git cannot know
- An inbox for captures, with promotion to a full initiative
- An optional single `path` per initiative, so `resume` lands the user where
  the work is
- A PowerShell module wrapping the binary to perform the directory change
- No **BREAKING** changes: greenfield project

### Assumptions recorded here

- The Phase 1 command list follows section 8 of the plan. Only `pause`,
  `resume` and `now` are "core"; the rest exist so the exit test can be run
  without hand-editing files, and each is kept to its minimum surface.
- `path` replaces the Phase 2 `workspaces` list for now. It is a single
  directory string, not validated against Git. Multi-repo workspaces remain
  out of scope.
- Interactive prompts pre-fill with the previous value and Enter keeps it.
  `wcm pause -n "<next>"` skips prompts entirely.
- On `new`, `--next` always sets the next action of the initiative being
  created; the one being switched away from is fed by `--pause-next`. One
  flag, one recipient.
- The plan's `milestone` checkpoint trigger is dropped in favour of `wait`
  and `done`, so every trigger names the command that produced it.
- `list` hides done initiatives unless `--all`. The plan's "archived after N
  days" nuance is not implemented: the `done/` directory already separates
  them, and a second threshold would be state without a use.
- No `config.yaml` is created in Phase 1. Nothing is configurable yet and
  `WCM_HOME` covers the only variation; it arrives with the Phase 2
  sensitive-repo list.
- Timestamps are local time with UTC offset (ISO 8601), matching the plan's
  examples.

## Capabilities

### New Capabilities
- `initiative-lifecycle`: states and transitions, the switch as the primitive
  operation, closing an initiative, and the invariants no transition may violate
- `initiative-context`: the five-field NOW block and the append-only checkpoints
  that precede it
- `working-set-view`: `wcm now` — the single screen answering what needs attention
- `inbox-capture`: capturing a concern without breaking focus, and promoting a
  capture into an initiative
- `memory-store`: plain-text memory that is hand-editable and reconstructible
  without the tool; derived IDs with no corruptible counter
- `shell-integration`: the protocol by which the CLI asks the parent shell to
  change directory, landing `resume` in the initiative's recorded path

### Modified Capabilities
(none — `openspec/specs/` contains no specs; this is greenfield)

## Impact

New Python 3.14 project (`src/wcm/`, tests under `tests/`) plus a small
PowerShell module (`shell/wcm.psm1`). Storage in `~/.wcm`, outside every
repository. No network, no LLM, no database. One runtime dependency at most
(a YAML library); everything else is standard library. Reading Git and
`~/.copilot` is deliberately deferred to later phases.

Out of scope, by design: agent integration, Git snapshots, multi-repo
workspaces, session discovery, context builder, attention queue, search,
and cross-machine sync. Phase 1's exit test is what defines their scope.
