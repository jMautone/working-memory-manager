## Why

Agent-assisted development multiplies the work a person can have in flight; it does not multiply their ability to remember where each thread stopped. That state lives in three fragile places — the person's head, open terminals, and chat history — and none of them answers "where was I and what's next?"

In the person's workflow this is three moments, and today each one is expensive:

- **Letting go** (pause): an interruption arrives and the current state is still in the head; writing it down somewhere costs more than 30 seconds, so it is not written.
- **Seeing** (now): from any terminal, there is no single place that says what is being attended and what is paused with a next action.
- **Picking up** (resume): days later, recovering what was being done means rereading chats.

This change builds the core that makes those three moments cost under 30 seconds. It is the first of five changes of Phase 1 (plan §14); notes, the inbox, knowledge bases and the remaining initiative commands come in the following changes.

## What Changes

The `wcm` CLI (Python 3.14) with the core commands, a plain-text store in a hub outside any repository, and a PowerShell module that performs the directory change. No **BREAKING** changes: greenfield project.

### Added

Commands:

- `wcm new "<title>"` with `--type`, `--priority`, `--path <dir>`, `--tags a,b`, `--focus`, `--why`, `--next`, `--pause-next`, `--paused`
- `wcm now`
- `wcm pause [ID]` with `-n/--next`, `-s/--stopped-at`, `-i/--important`
- `wcm resume [ID]` (no ID or the active ID: re-show the active initiative's brief and request the directory change)
- `wcm done [ID]`
- IDs accepted as `INIT-0007`, `init-7` or `7`, case-insensitively
- Exit codes: `0` success, `1` domain error, `2` usage error

Environment variables:

- `WCM_HOME`: overrides the hub, `~/.wcm` by default
- `WCM_CD_FILE`: set by the shell wrapper; the CLI writes the directory to change to

Files, under `<hub>/kbs/work/`:

- `initiatives/<ID>/<ID>.md` and `done/<ID>/<ID>.md`: YAML frontmatter with `id`, `title`, `type`, `status`, `priority`, `created`, `updated`, `last_resumed`, `last_paused`, `waiting_on`, `tags`, `workspaces` (entries with `path` and `primary`), `links`, and `closed` once done; body with `# <title>` and a `## NOW` block of five fields (`Focus`, `Stopped at`, `Why it matters`, `Important`, `Next`)
- `initiatives/<ID>/checkpoints/<YYYY-MM-DD>T<HHMMSS>.md`: append-only, with `Author:`, `Trigger:` (`pause`, `switch`, `done`) and six sections

Shell:

- `shell/wcm.psm1`: a `wcm` function that wraps the CLI and changes location through `WCM_CD_FILE`

`wcm now` also flags an active initiative that has gone more than 4 hours without a checkpoint.

### Modified

Nothing: there is no previous version.

### Removed

Nothing.

### Assumptions recorded here

- Interactive prompts pre-fill with the previous value and Enter keeps it. `wcm pause -n "<next>"` skips prompts entirely.
- On `new`, `--next` always sets the next action of the initiative being created; the one being switched away from is fed by `--pause-next`. One flag, one recipient.
- `waiting` is one of the four states of the file format, but no command of this change reaches it: `wcm wait` arrives with `add-initiative-tools`. A waiting initiative written by hand is shown as a warning line in `now`, never hidden.
- No `config.yaml` is created: nothing is configurable yet and `WCM_HOME` covers the only variation. It arrives with `add-knowledge-bases`. The 4-hour threshold is fixed until then.
- Timestamps are local time with UTC offset (ISO 8601).

## Fase

- **Phase**: F1 SWITCH (plan §14), change 1 of 5. Next: `add-notes`, `add-inbox`, `add-knowledge-bases`, `add-initiative-tools`.
- **Branch**: `v0.1/add-working-memory-layer`.
- **Version**: publishes `v0.1.0-alpha.1`.
- Real daily use and the Phase 1 simulation start with this alpha. The exit test closes after the last alpha of F1, before `release/v0.1.0`; it is not a task of this change.

## Non-goals

- Notes, `wcm note`/`notes` (`add-notes`).
- The inbox: `capture`, `inbox`, `promote`, `drop` (`add-inbox`).
- Several knowledge bases, `config.yaml`, `kb new`/`kb list`, `-k` (`add-knowledge-bases`).
- `wait`, `list`, `show`, `checkpoint`, `edit`, and the WAITING section of `now` (`add-initiative-tools`).
- Git snapshots, multi-repo workspaces, session discovery, CWD resolution (F2).
- Agent checkpoints, context builder, agent-maintained wikis (F3).
- Attention queue beyond the single stale-active warning, `wrap` (F4).
- Search, sync between machines.
- Colour or rich terminal UI.
- Shell wrappers other than PowerShell.

## OS impact

- The automatic directory change works only through the PowerShell module in this change, so only on Windows (PowerShell 5.1) in practice. On macOS and Linux every command works and `resume` prints the `Path:` line, but the shell stays where it was.
- Paths are stored as the OS writes them (`C:\...` on Windows, `/...` elsewhere). Everything else behaves the same on the three OSes.

## Capabilities

### New Capabilities
- `initiative-lifecycle`: states and transitions, the switch as the primitive operation, resuming the active initiative again, closing, exit codes, and the invariants no transition may violate
- `initiative-context`: the five-field NOW block under the title heading, the pause flow, append-only checkpoints and the resume brief
- `working-set-view`: `wcm now` — the single screen answering what needs attention, including the stale-active warning
- `memory-store`: the hub and the `work` knowledge base, files named by ID, hand-editable plain text, derived IDs with no counter
- `shell-integration`: the protocol by which the CLI asks the parent shell to change directory, and the PowerShell module that honours it

### Modified Capabilities
(none — `openspec/specs/` contains no specs; this is greenfield)

## Impact

New Python 3.14 project (`src/wcm/`, tests under `tests/`) plus a small PowerShell module (`shell/wcm.psm1`). Storage in `~/.wcm/kbs/work/`, outside every repository and openable as an Obsidian vault. No network, no LLM, no database. One runtime dependency (a YAML library); everything else is standard library.

The decisions behind the layout, the file naming and the split of Phase 1 are in `docs/decisions/0002-notas-y-bases-de-conocimiento.md`.
