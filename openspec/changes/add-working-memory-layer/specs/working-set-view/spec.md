## Purpose

`wcm now` is the person's external memory: one terminal screen, from any directory, answering what is being attended, what is paused with a next action, what is waiting, what sits in the inbox, and what looks wrong.

## ADDED Requirements

### Requirement: One screen with fixed sections
`wcm now` SHALL print, in this order, the sections `ACTIVE`, `PAUSED` and `WAITING`, each listing its initiatives, then an `INBOX` line with the number of unprocessed captures, then warning lines prefixed with `!`. A section with no initiatives SHALL be omitted. The `INBOX` line SHALL be omitted when the inbox is empty. When there are no initiatives at all and the inbox is empty, the command SHALL print a single line saying nothing is in flight and suggesting `wcm new` or `wcm capture`.

#### Scenario: Typical working set
- **WHEN** one initiative is active, two are paused, one is waiting and the inbox holds three captures
- **THEN** the output contains the headings `ACTIVE`, `PAUSED`, `WAITING`, one entry under each with the right initiatives, and a line `INBOX  3 captures`

#### Scenario: Empty store
- **WHEN** the store has no initiatives and no captures
- **THEN** the output is one line mentioning `wcm new` and `wcm capture`, and the exit code is zero

#### Scenario: Nothing active
- **WHEN** no initiative is active and two are paused
- **THEN** the output has no `ACTIVE` heading and lists both under `PAUSED`

### Requirement: Two lines per initiative
Each initiative SHALL occupy exactly two lines. Line one: ID, title, priority (shown only when not `normal`), and age. Line two, indented: `Next: <text>` for active and paused initiatives, or `on: <what> (owner: <owner>)` for waiting ones. The second line SHALL be truncated with an ellipsis so it never wraps at the current terminal width (or 100 columns when the width is unknown).

#### Scenario: Priority shown only when notable
- **WHEN** `INIT-0008` has priority `critical` and `INIT-0007` has priority `normal`
- **THEN** the line for `INIT-0008` contains `critical` and the line for `INIT-0007` contains no priority word

#### Scenario: Long next action is truncated
- **WHEN** an initiative's `Next` is 300 characters long and the terminal is 80 columns wide
- **THEN** its second line is at most 80 characters and ends with `…`

#### Scenario: Waiting shows what it waits on
- **WHEN** `INIT-0003` is waiting on `architecture approval` with owner `Ana`
- **THEN** its second line reads `on: architecture approval (owner: Ana)`

### Requirement: Age reflects the state
The age shown SHALL be computed from `last_resumed` for active initiatives, `last_paused` for paused ones, and `waiting_on.since` for waiting ones, rendered compactly (`23m`, `1h 23m`, `2d`, `3w`). An initiative missing the relevant timestamp SHALL show `?` instead of an age.

#### Scenario: Paused two days ago
- **WHEN** `INIT-0007` has `last_paused` 50 hours before now
- **THEN** its first line shows `2d`

#### Scenario: Missing timestamp
- **WHEN** a hand-written paused initiative has `last_paused: null`
- **THEN** its first line shows `?` where the age would be

### Requirement: Ordering within a section
Within `PAUSED` and `WAITING`, initiatives SHALL be ordered by priority (`critical`, `high`, `normal`, `low`) and then by the state timestamp, most recent first.

#### Scenario: Priority before recency
- **WHEN** `INIT-0005` is `high` and paused five days ago and `INIT-0007` is `normal` and paused one hour ago
- **THEN** `INIT-0005` is listed before `INIT-0007` under `PAUSED`

### Requirement: Warnings are shown, not fixed
After the sections, `wcm now` SHALL print one `!` line per detected problem: more than one active initiative; a paused or waiting initiative without `Next`; a waiting initiative without `waiting_on.what`; a NOW block over 15 lines; an initiative file that could not be parsed; a recorded `path` that does not exist on disk. The command SHALL exit zero even when warnings are printed and SHALL NOT modify any file.

#### Scenario: Missing path warned
- **WHEN** `INIT-0007` records `path: C:\wt\gone` and that directory does not exist
- **THEN** the output contains a `!` line naming `INIT-0007` and the missing path, and the exit code is zero

#### Scenario: Two active warned
- **WHEN** two initiatives are active on disk
- **THEN** both appear under `ACTIVE` and a `!` line says more than one initiative is active

### Requirement: Independent of the current directory
`wcm now` SHALL read only the storage root and SHALL produce the same output regardless of the directory it is run from.

#### Scenario: Run from two directories
- **WHEN** the user runs `wcm now` from `C:\` and again from inside a Git worktree
- **THEN** both outputs are identical
