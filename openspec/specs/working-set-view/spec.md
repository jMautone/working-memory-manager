# working-set-view Specification

## Purpose

`wcm now` is the person's external memory: one terminal screen, from any directory, answering what is being attended, what is paused with a next action, and what looks wrong.

## Requirements
### Requirement: One screen with fixed sections
`wcm now` SHALL print, in this order, the sections `ACTIVE` and `PAUSED`, each listing its initiatives, then warning lines prefixed with `!`. A section with no initiatives SHALL be omitted. When there are no initiatives in `active`, `paused` or `waiting` state, the command SHALL print a single line saying nothing is in flight and suggesting `wcm new`.

#### Scenario: Typical working set
- **WHEN** one initiative is active and two are paused
- **THEN** the output contains the headings `ACTIVE` and `PAUSED` with the right initiatives under each

#### Scenario: Empty store
- **WHEN** the store has no initiatives
- **THEN** the output is one line mentioning `wcm new`, and the exit code is zero

#### Scenario: Nothing active
- **WHEN** no initiative is active and two are paused
- **THEN** the output has no `ACTIVE` heading and lists both under `PAUSED`

### Requirement: Two lines per initiative
Each listed initiative SHALL occupy exactly two lines. Line one: ID, title, priority (shown only when not `normal`), and age. Line two, indented: `Next: <text>`. The second line SHALL be truncated with an ellipsis so it never wraps at the current terminal width (or 100 columns when the width is unknown).

#### Scenario: Priority shown only when notable
- **WHEN** `INIT-0008` has priority `critical` and `INIT-0007` has priority `normal`
- **THEN** the line for `INIT-0008` contains `critical` and the line for `INIT-0007` contains no priority word

#### Scenario: Long next action is truncated
- **WHEN** an initiative's `Next` is 300 characters long and the terminal is 80 columns wide
- **THEN** its second line is at most 80 characters and ends with `…`

### Requirement: Age reflects the state
The age shown SHALL be computed from `last_resumed` for active initiatives and `last_paused` for paused ones, rendered compactly (`23m`, `1h 23m`, `2d`, `3w`). An initiative missing the relevant timestamp SHALL show `?` instead of an age.

#### Scenario: Paused two days ago
- **WHEN** `INIT-0007` has `last_paused` 50 hours before now
- **THEN** its first line shows `2d`

#### Scenario: Missing timestamp
- **WHEN** a hand-written paused initiative has `last_paused: null`
- **THEN** its first line shows `?` where the age would be

### Requirement: Ordering within a section
Within `PAUSED`, initiatives SHALL be ordered by priority (`critical`, `high`, `normal`, `low`) and then by `last_paused`, most recent first.

#### Scenario: Priority before recency
- **WHEN** `INIT-0005` is `high` and paused five days ago and `INIT-0007` is `normal` and paused one hour ago
- **THEN** `INIT-0005` is listed before `INIT-0007` under `PAUSED`

### Requirement: Stale active initiative is flagged
When the active initiative has gone more than 4 hours without a checkpoint, counted from the most recent of its `last_resumed` and the time of its latest checkpoint, `wcm now` SHALL print a `!` line naming it, saying how long it has been active without a checkpoint and suggesting `wcm pause`.

#### Scenario: Active for six hours
- **WHEN** `INIT-0008` was resumed 6 hours ago and has no checkpoint since then
- **THEN** the output contains a `!` line naming `INIT-0008`, `6h` and `wcm pause`

#### Scenario: Recently resumed after a long pause
- **WHEN** `INIT-0007`'s latest checkpoint is three days old and it was resumed 30 minutes ago
- **THEN** no stale line is printed for `INIT-0007`

### Requirement: Warnings are shown, not fixed
After the sections, `wcm now` SHALL print one `!` line per detected problem: more than one active initiative; a paused initiative without `Next`; a waiting initiative, naming what it waits on, since waiting initiatives have no section; a waiting initiative without `waiting_on.what`; a NOW block over 15 lines; an initiative file that could not be parsed; a primary workspace path that does not exist on disk; a stale active initiative. The command SHALL exit zero even when warnings are printed and SHALL NOT modify any file.

#### Scenario: Missing path warned
- **WHEN** `INIT-0007`'s primary workspace path does not exist on disk
- **THEN** the output contains a `!` line naming `INIT-0007` and the missing path, and the exit code is zero

#### Scenario: Two active warned
- **WHEN** two initiatives are active on disk
- **THEN** both appear under `ACTIVE` and a `!` line says more than one initiative is active

#### Scenario: Waiting initiative is not hidden
- **WHEN** `INIT-0003` has `status: waiting` with `waiting_on.what: architecture approval`, written by hand
- **THEN** the output contains a `!` line naming `INIT-0003` and `architecture approval`

### Requirement: Independent of the current directory
`wcm now` SHALL read only the storage root and SHALL produce the same output regardless of the directory it is run from.

#### Scenario: Run from two directories
- **WHEN** the user runs `wcm now` from the filesystem root and again from inside a Git worktree
- **THEN** both outputs are identical

