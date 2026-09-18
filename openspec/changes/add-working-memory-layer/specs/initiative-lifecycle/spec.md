## Purpose

Defines the four initiative states, the switch as the one primitive transition, how an initiative is created and closed, and the invariants that no transition may violate. Everything else in WCM exists to make switching cheap.

## ADDED Requirements

### Requirement: Four states
An initiative SHALL be in exactly one of four states: `active` (what the person is attending now), `paused` (interrupted deliberately, has a next action), `waiting` (cannot progress, records what it waits on), `done` (objective met). No other state value SHALL be accepted. "Ready" and "blocked" are not states: ready is `paused` with `last_resumed: null`; blocked is `waiting` whose owner is `me`.

#### Scenario: Unknown state rejected on read
- **WHEN** an initiative file has `status: archived`
- **THEN** it is reported as malformed and is not shown under any state section

### Requirement: At most one active initiative
The system SHALL never leave more than one initiative in `active` state as a result of its own commands. If it finds more than one active initiative on disk (for example after a hand edit), commands that would activate an initiative (`new`, `resume`, `promote --resume`) SHALL refuse, name the conflicting files, and change nothing.

#### Scenario: Two active on disk
- **WHEN** `INIT-0003` and `INIT-0004` both have `status: active` and the user runs `wcm resume INIT-0007`
- **THEN** the command exits non-zero, names both files, and all three initiatives are unchanged

### Requirement: Create an initiative
`wcm new "<title>"` SHALL create an initiative with the given title and make it active, performing the switch flow on any previously active initiative first. Options: `--type` (feature | bug | incident | research | refactor | other; default `other`), `--priority` (critical | high | normal | low; default `normal`), `--path <dir>`, `--tags a,b`, `--focus "<text>"`, `--why "<text>"`. With `--paused`, the initiative SHALL be created in `paused` state without touching the current active one; `--paused` REQUIRES `--next "<text>"`. The command SHALL print the new ID and its state.

#### Scenario: First initiative becomes active
- **WHEN** no initiative is active and the user runs `wcm new "Payment retries"`
- **THEN** `INIT-0007` is created with `status: active`, `last_resumed` set to now, and the output contains `INIT-0007 active`

#### Scenario: Creating while another is active switches
- **WHEN** `INIT-0007` is active and the user runs `wcm new "Login incident" --type incident --priority critical -n "Reproduce the lockout race"`
- **THEN** `INIT-0007` goes through the pause flow with `-n` applied to it, becomes `paused`, and `INIT-0008` becomes `active`

#### Scenario: Paused creation needs a next action
- **WHEN** the user runs `wcm new "Later thing" --paused` without `--next`
- **THEN** the command exits non-zero, explains that a paused initiative needs a next action, and nothing is created

### Requirement: Switch is the primitive
`wcm resume <ID>` SHALL, in order: run the pause flow on the currently active initiative if there is one and it is not the target (its checkpoint trigger is `switch`); set the target to `active`; set its `last_resumed` to now; clear `waiting_on` if the target was waiting; print the resume brief. If the target is already active the command SHALL say so and change nothing. A `done` initiative SHALL NOT be resumable; the command SHALL point the user to hand-moving the directory out of `done/` as the escape valve.

#### Scenario: Resume with another active
- **WHEN** `INIT-0008` is active with a filled `Next`, `INIT-0007` is paused, and the user runs `wcm resume INIT-0007` and presses Enter at each prompt
- **THEN** `INIT-0008` is `paused` with a new checkpoint whose trigger is `switch`, `INIT-0007` is `active`, and `INIT-0007.last_resumed` is now

#### Scenario: Resume a waiting initiative
- **WHEN** `INIT-0003` is `waiting` and the user runs `wcm resume INIT-0003`
- **THEN** `INIT-0003` is `active` and its `waiting_on` is `null`

#### Scenario: Resume the already active one
- **WHEN** `INIT-0007` is active and the user runs `wcm resume INIT-0007`
- **THEN** the command prints that it is already active, exits zero, and writes no checkpoint

#### Scenario: Resume a done initiative
- **WHEN** `INIT-0002` is under `done/` and the user runs `wcm resume INIT-0002`
- **THEN** the command exits non-zero and explains how to reopen it by hand

#### Scenario: Resume without an ID
- **WHEN** the user runs `wcm resume` with no argument
- **THEN** the command lists the paused and waiting initiatives with their IDs and exits non-zero

#### Scenario: Resume an unknown ID
- **WHEN** the user runs `wcm resume INIT-0099` and no such initiative exists
- **THEN** the command exits non-zero and says the ID was not found

### Requirement: Pause is a switch to nothing
`wcm pause [ID]` SHALL target the active initiative when no ID is given. It SHALL run the pause flow (see `initiative-context`), then set `status: paused`, `last_paused` to now, and clear `waiting_on`. When no ID is given and nothing is active, the command SHALL say so and exit non-zero without changing anything. Pausing an initiative that is already paused SHALL be allowed and SHALL refresh its NOW block and write a checkpoint.

#### Scenario: Pause the active initiative
- **WHEN** `INIT-0007` is active and the user runs `wcm pause -n "Finish PaymentRetryPolicy"`
- **THEN** `INIT-0007` is `paused`, `last_paused` is now, no initiative is active, and the output ends with `Safe to switch context.`

#### Scenario: Nothing to pause
- **WHEN** no initiative is active and the user runs `wcm pause`
- **THEN** the command prints that nothing is active and exits non-zero

#### Scenario: Pause refuses without a next action
- **WHEN** `INIT-0007` is active, its `Next` is empty, and the user presses Enter at the `Next action` prompt
- **THEN** the command explains that a next action is required, `INIT-0007` stays `active`, and no checkpoint is written

### Requirement: Wait on something
`wcm wait [ID] --on "<what>" [--owner <name>]` SHALL set the target to `waiting` with `waiting_on: {what, owner, since}` where `owner` defaults to `me` and `since` is now. `--on` is required and SHALL be non-empty. If the target is active, the pause flow SHALL run first so the NOW block is fresh. Without an ID the target is the active initiative.

#### Scenario: Active initiative starts waiting
- **WHEN** `INIT-0003` is active and the user runs `wcm wait --on "architecture approval" --owner Ana -n "Apply the review notes"`
- **THEN** `INIT-0003` is `waiting`, `waiting_on.what` is `architecture approval`, `waiting_on.owner` is `Ana`, its `Next` is `Apply the review notes`, and no initiative is active

#### Scenario: Wait requires a reason
- **WHEN** the user runs `wcm wait INIT-0003 --on ""`
- **THEN** the command exits non-zero and `INIT-0003` is unchanged

### Requirement: Close an initiative
`wcm done [ID]` SHALL set `status: done`, record a `closed` timestamp, write a final checkpoint with trigger `done`, and move the directory to `done/`. A next action is not required to close. Without an ID the target is the active initiative. Closing an initiative that is already done SHALL fail.

#### Scenario: Close the active initiative
- **WHEN** `INIT-0008` is active and the user runs `wcm done`
- **THEN** `done/INIT-0008-*/initiative.md` has `status: done` and a `closed` timestamp, a checkpoint with `Trigger: done` exists in that directory, and no initiative is active

#### Scenario: Close a paused initiative
- **WHEN** `INIT-0005` is paused and `INIT-0007` is active and the user runs `wcm done INIT-0005`
- **THEN** `INIT-0005` is under `done/` and `INIT-0007` is still active

### Requirement: Invariants hold after every transition
After any command completes, the store SHALL satisfy: at most one `active`; every `paused` initiative has a non-empty `Next`; every `waiting` initiative has a non-empty `waiting_on.what`. A command whose result would violate an invariant SHALL refuse before writing. Violations introduced by hand edits SHALL be reported as warnings by `wcm now` and `wcm list`, never repaired automatically.

#### Scenario: Hand-edited paused initiative without Next
- **WHEN** the user blanks the `Next` field of a paused initiative by hand and runs `wcm now`
- **THEN** the initiative is still listed under PAUSED and a warning line says it has no next action

### Requirement: List and show
`wcm list` SHALL print every initiative that is not done, one per line with ID, state, priority, title and age, sorted by state (active, paused, waiting) then priority then most recent activity. `--all` SHALL include done initiatives. `wcm show [ID]` SHALL print the frontmatter summary (ID, title, type, state, priority, tags, path, timestamps, waiting_on), the NOW block, the number of checkpoints and the path of the most recent one. Without an ID, `show` targets the active initiative.

#### Scenario: List hides done by default
- **WHEN** `INIT-0002` is done and `INIT-0007` is paused and the user runs `wcm list`
- **THEN** the output contains `INIT-0007` and not `INIT-0002`

#### Scenario: Show the active initiative
- **WHEN** `INIT-0007` is active with two checkpoints and the user runs `wcm show`
- **THEN** the output contains `INIT-0007`, its NOW block, `Checkpoints: 2` and the path of the latest checkpoint file

### Requirement: Edit as the escape valve
`wcm edit [ID]` SHALL open the initiative's `initiative.md` in the editor named by `VISUAL`, else `EDITOR`, else `notepad`, wait for it to exit, then re-read the file and print any warnings about malformed content or violated invariants.

#### Scenario: Edit then validate
- **WHEN** `EDITOR` is set to a program that removes the `status` line and the user runs `wcm edit INIT-0007`
- **THEN** after the editor exits the command prints a warning that `INIT-0007` is malformed and exits non-zero

### Requirement: Target resolution without an ID
Commands that accept an optional ID (`pause`, `wait`, `done`, `show`, `edit`, `checkpoint`) SHALL target the active initiative when the ID is omitted, and SHALL fail with a message when there is no active initiative. No command SHALL guess among several candidates.

#### Scenario: No active for show
- **WHEN** nothing is active and the user runs `wcm show`
- **THEN** the command says there is no active initiative, suggests `wcm list`, and exits non-zero
