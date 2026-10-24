# initiative-lifecycle Specification

## Purpose

Defines the four initiative states, the switch as the one primitive transition, how an initiative is created and closed, and the invariants that no transition may violate. Everything else in WCM exists to make switching cheap.

## Requirements
### Requirement: Four states
An initiative SHALL be in exactly one of four states: `active` (what the person is attending now), `paused` (interrupted deliberately, has a next action), `waiting` (cannot progress, records what it waits on), `done` (objective met). No other state value SHALL be accepted. "Ready" and "blocked" are not states: ready is `paused` with `last_resumed: null`; blocked is `waiting` whose owner is `me`.

#### Scenario: Unknown state rejected on read
- **WHEN** an initiative file has `status: archived`
- **THEN** it is reported as malformed and is not shown under any state section

### Requirement: Exit codes
Every command SHALL exit with code 0 on success, 1 on a domain error (unknown ID, malformed file, a refused transition, nothing to act on) and 2 on a usage error (unknown command, missing or invalid argument). Errors SHALL be printed on stderr.

#### Scenario: Unknown command
- **WHEN** the user runs `wcm frobnicate`
- **THEN** the command exits with code 2 and prints usage on stderr

### Requirement: At most one active initiative
The system SHALL never leave more than one initiative in `active` state as a result of its own commands. If it finds more than one active initiative on disk (for example after a hand edit), commands that would activate an initiative (`new`, `resume`) SHALL refuse, name the conflicting files, exit with code 1 and change nothing.

#### Scenario: Two active on disk
- **WHEN** `INIT-0003` and `INIT-0004` both have `status: active` and the user runs `wcm resume INIT-0007`
- **THEN** the command exits with code 1, names both files, and all three initiatives are unchanged

### Requirement: Create an initiative
`wcm new "<title>"` SHALL create an initiative with the given title and make it active, performing the switch flow on any previously active initiative first. Options: `--type` (feature | bug | incident | research | refactor | other; default `other`), `--priority` (critical | high | normal | low; default `normal`), `--path <dir>`, `--tags a,b`, `--focus "<text>"`, `--why "<text>"`, `--next "<text>"`, `--pause-next "<text>"`. `--path` SHALL record the directory, made absolute, as the single primary entry of `workspaces`; a directory that does not exist SHALL be recorded anyway with a warning. `--next` SHALL set the `Next` field of the initiative being created and SHALL NEVER be applied to the one being paused; `--pause-next` SHALL feed the pause flow of the previously active initiative so a switch needs no prompt. With `--paused`, the initiative SHALL be created in `paused` state without touching the current active one; `--paused` REQUIRES `--next "<text>"`. The command SHALL print the new ID and its state.

#### Scenario: First initiative becomes active
- **WHEN** no initiative is active and the user runs `wcm new "Payment retries"`
- **THEN** `INIT-0007` is created with `status: active`, `last_resumed` set to now, and the output contains `INIT-0007 active`

#### Scenario: Creating while another is active switches
- **WHEN** `INIT-0007` is active and the user runs `wcm new "Login incident" --type incident --priority critical --next "Reproduce the lockout race" --pause-next "Finish PaymentRetryPolicy"`
- **THEN** `INIT-0007` becomes `paused` with `Next: Finish PaymentRetryPolicy`, `INIT-0008` becomes `active` with `Next: Reproduce the lockout race`, and no prompt is shown

#### Scenario: Paused creation needs a next action
- **WHEN** the user runs `wcm new "Later thing" --paused` without `--next`
- **THEN** the command exits with code 1, explains that a paused initiative needs a next action, and nothing is created

#### Scenario: Path that does not exist
- **WHEN** the user runs `wcm new "Spike" --path <dir>` and `<dir>` does not exist
- **THEN** the initiative is created with `<dir>` as its primary workspace path and the output warns that the directory does not exist

### Requirement: Switch is the primitive
`wcm resume <ID>` SHALL, in order: run the pause flow on the currently active initiative if there is one and it is not the target (its checkpoint trigger is `switch`); set the target to `active`; set its `last_resumed` to now; clear `waiting_on` if the target was waiting; print the resume brief. A `done` initiative SHALL NOT be resumable; the command SHALL point the user to hand-moving the directory out of `done/` as the escape valve.

#### Scenario: Resume with another active
- **WHEN** `INIT-0008` is active with a filled `Next`, `INIT-0007` is paused, and the user runs `wcm resume INIT-0007` and presses Enter at each prompt
- **THEN** `INIT-0008` is `paused` with a new checkpoint whose trigger is `switch`, `INIT-0007` is `active`, and `INIT-0007.last_resumed` is now

#### Scenario: Resume a waiting initiative
- **WHEN** `INIT-0003` is `waiting` and the user runs `wcm resume INIT-0003`
- **THEN** `INIT-0003` is `active` and its `waiting_on` is `null`

#### Scenario: Resume a done initiative
- **WHEN** `INIT-0002` is under `done/` and the user runs `wcm resume INIT-0002`
- **THEN** the command exits with code 1 and explains how to reopen it by hand

#### Scenario: Resume an unknown ID
- **WHEN** the user runs `wcm resume INIT-0099` and no such initiative exists
- **THEN** the command exits with code 1 and says the ID was not found

### Requirement: Resume the active initiative again
`wcm resume` with no ID, or with the ID of the initiative that is already active, SHALL print that initiative's resume brief and request the directory change (see `shell-integration`), without writing a checkpoint, without changing any field and exiting with code 0. With no ID and no active initiative, the command SHALL list the paused and waiting initiatives with their IDs and exit with code 1.

#### Scenario: Back in a new terminal
- **WHEN** `INIT-0007` is active and the user runs `wcm resume`
- **THEN** the brief of `INIT-0007` is printed, no checkpoint is written, `INIT-0007`'s file is unchanged and the exit code is 0

#### Scenario: Resume the active one by ID
- **WHEN** `INIT-0007` is active and the user runs `wcm resume INIT-0007`
- **THEN** the output and effects are the same as for `wcm resume` with no ID

#### Scenario: Nothing active and no ID
- **WHEN** no initiative is active, `INIT-0005` and `INIT-0007` are paused, and the user runs `wcm resume`
- **THEN** the output lists `INIT-0005` and `INIT-0007` and the exit code is 1

### Requirement: Pause is a switch to nothing
`wcm pause [ID]` SHALL target the active initiative when no ID is given. It SHALL run the pause flow (see `initiative-context`), then set `status: paused`, `last_paused` to now, and clear `waiting_on`. When no ID is given and nothing is active, the command SHALL say so and exit with code 1 without changing anything. Pausing an initiative that is already paused SHALL be allowed and SHALL refresh its NOW block and write a checkpoint.

#### Scenario: Pause the active initiative
- **WHEN** `INIT-0007` is active and the user runs `wcm pause -n "Finish PaymentRetryPolicy"`
- **THEN** `INIT-0007` is `paused`, `last_paused` is now, no initiative is active, and the output ends with `Safe to switch context.`

#### Scenario: Nothing to pause
- **WHEN** no initiative is active and the user runs `wcm pause`
- **THEN** the command prints that nothing is active and exits with code 1

#### Scenario: Pause refuses without a next action
- **WHEN** `INIT-0007` is active, its `Next` is empty, and the user presses Enter at the `Next action` prompt
- **THEN** the command explains that a next action is required, exits with code 1, `INIT-0007` stays `active`, and no checkpoint is written

### Requirement: Close an initiative
`wcm done [ID]` SHALL set `status: done`, record a `closed` timestamp, write a final checkpoint with trigger `done`, and move the directory to `done/`. A next action is not required to close. Closing a `waiting` initiative SHALL keep its `waiting_on` value as the record of why the work ended there. Without an ID the target is the active initiative. Closing an initiative that is already done SHALL fail with code 1.

#### Scenario: Close the active initiative
- **WHEN** `INIT-0008` is active and the user runs `wcm done`
- **THEN** `done/INIT-0008/INIT-0008.md` has `status: done` and a `closed` timestamp, a checkpoint with `Trigger: done` exists in that directory, and no initiative is active

#### Scenario: Close a paused initiative
- **WHEN** `INIT-0005` is paused and `INIT-0007` is active and the user runs `wcm done INIT-0005`
- **THEN** `INIT-0005` is under `done/` and `INIT-0007` is still active

#### Scenario: Close a waiting initiative
- **WHEN** `INIT-0003` is waiting on `architecture approval` and the user runs `wcm done INIT-0003`
- **THEN** `INIT-0003` is under `done/` with `status: done` and a `closed` timestamp, and its `waiting_on.what` still reads `architecture approval`

### Requirement: Invariants hold after every transition
After any command completes, the store SHALL satisfy: at most one `active`; every `paused` initiative has a non-empty `Next`; every `waiting` initiative has a non-empty `waiting_on.what`. A command whose result would violate an invariant SHALL refuse before writing. Violations introduced by hand edits SHALL be reported as warnings by `wcm now`, never repaired automatically.

#### Scenario: Hand-edited paused initiative without Next
- **WHEN** the user blanks the `Next` field of a paused initiative by hand and runs `wcm now`
- **THEN** the initiative is still listed under PAUSED and a warning line says it has no next action

### Requirement: Target resolution without an ID
Commands that accept an optional ID (`pause`, `done`) SHALL target the active initiative when the ID is omitted, and SHALL fail with code 1 and a message suggesting `wcm now` when there is no active initiative. No command SHALL guess among several candidates.

#### Scenario: No active for done
- **WHEN** nothing is active and the user runs `wcm done`
- **THEN** the command says there is no active initiative, suggests `wcm now`, exits with code 1 and changes nothing

