## Purpose

Lets a person record a new concern in one command without leaving the initiative they are attending, and later turn that capture into a full initiative once it deserves attention.

## ADDED Requirements

### Requirement: Capture without breaking focus
`wcm capture <text...>` SHALL append one line to `inbox.md` in the form `- <YYYY-MM-DD>T<HH:MM> CAP-<NNNN> <text>` (local time), creating the file if needed, and SHALL print the assigned capture ID. Remaining command-line words SHALL be joined with single spaces so quotes are optional. Line breaks in the text SHALL be replaced by spaces. The command SHALL NOT change the state, timestamps or NOW block of any initiative. Empty text SHALL be rejected.

#### Scenario: Capture while active
- **WHEN** `INIT-0007` is active and the user runs `wcm capture Check possible refresh token leak`
- **THEN** `inbox.md` ends with a line matching `- 2026-..T..:.. CAP-0001 Check possible refresh token leak`, the output contains `CAP-0001`, and `INIT-0007` is unchanged including its `updated` timestamp

#### Scenario: Empty capture rejected
- **WHEN** the user runs `wcm capture ""`
- **THEN** the command exits non-zero and `inbox.md` is unchanged

### Requirement: Capture IDs are derived
The next capture ID SHALL be one greater than the highest `CAP-<NNNN>` found in `inbox.md` lines and in the `capture` frontmatter field of every initiative under `initiatives/` and `done/`. The system SHALL NOT keep a counter file, and a promoted capture's ID SHALL NOT be reused.

#### Scenario: ID survives promotion
- **WHEN** `CAP-0003` is the only capture, it is promoted, and the user runs `wcm capture Another thing`
- **THEN** the new capture receives `CAP-0004`

### Requirement: List the inbox
`wcm inbox` SHALL list every capture in `inbox.md`, oldest first, showing its ID, age and text. Lines that do not match the capture format SHALL be ignored by the listing but preserved in the file. When there are no captures the command SHALL print that the inbox is empty.

#### Scenario: Two captures listed
- **WHEN** `inbox.md` holds `CAP-0027` captured two hours ago and `CAP-0028` captured ten minutes ago
- **THEN** the output lists `CAP-0027` with `2h` before `CAP-0028` with `10m`

#### Scenario: Empty inbox
- **WHEN** `inbox.md` does not exist
- **THEN** the output says the inbox is empty and the exit code is zero

### Requirement: Promote a capture into an initiative
`wcm promote CAP-<NNNN>` SHALL remove that line from `inbox.md`, create a new initiative whose title is the capture text (overridable with `--title`), whose `Next` is the capture text, whose frontmatter records `capture: CAP-<NNNN>`, and whose state is `paused`. The options `--type`, `--priority`, `--path` and `--tags` SHALL be accepted as in `wcm new`. With `--resume` the new initiative SHALL instead be activated through the switch flow. The command SHALL print the new initiative ID. All other lines of `inbox.md`, including non-matching ones, SHALL be preserved verbatim.

#### Scenario: Promote to paused
- **WHEN** the inbox holds `CAP-0027 Check possible refresh token leak` and `INIT-0007` is active, and the user runs `wcm promote CAP-0027`
- **THEN** a new initiative exists with title `Check possible refresh token leak`, `status: paused`, `capture: CAP-0027`, `Next: Check possible refresh token leak`; the `CAP-0027` line is gone from `inbox.md`; and `INIT-0007` is still active

#### Scenario: Promote and resume
- **WHEN** `INIT-0007` is active with a filled `Next` and the user runs `wcm promote CAP-0027 --resume` and presses Enter at each prompt
- **THEN** `INIT-0007` is paused and the new initiative is active

#### Scenario: Unknown capture
- **WHEN** the user runs `wcm promote CAP-0099` and no such line exists
- **THEN** the command exits non-zero, says the capture was not found, and `inbox.md` is unchanged

#### Scenario: Other lines preserved
- **WHEN** `inbox.md` also contains a hand-written line `TODO clean this up` and the user promotes `CAP-0027`
- **THEN** `inbox.md` still contains `TODO clean this up` in its original position
