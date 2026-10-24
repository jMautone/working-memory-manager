# Spec Delta

## MODIFIED Requirements

### Requirement: Resume brief
`wcm resume` SHALL print, after any switch, a brief consisting of the ID and title, how long ago it was paused (or since when it was waiting, with what it waited on), then each non-empty NOW field in order (`Focus`, `Stopped at`, `Why it matters`, `Important`, `Next`), then, when at least one valid note links to the initiative, `Notes:` with the number of linked notes and the title of the most recently created one as `<count> (latest: <title>)`, then `Path:` with the primary workspace path when one is recorded. The brief SHALL NOT include checkpoints, history, or the body of any note. The same brief SHALL be printed by `wcm resume` with no ID or with the ID of the active initiative.

#### Scenario: Brief after two days
- **WHEN** `INIT-0007` was paused two days ago with all five fields filled and a primary workspace path, and the user runs `wcm resume INIT-0007`
- **THEN** the output contains `INIT-0007`, `Payment retries`, `paused 2d ago`, the five field values and a `Path:` line

#### Scenario: Empty fields are skipped
- **WHEN** `INIT-0009` has empty `Stopped at` and `Important` fields
- **THEN** the brief printed by `wcm resume INIT-0009` contains no `Stopped at` or `Important` lines

#### Scenario: Brief with linked notes
- **WHEN** three valid notes link to `INIT-0007`, the most recently created titled `the gateway cuts at 30s, not 60`, and the user runs `wcm resume INIT-0007`
- **THEN** the brief contains `Notes:` followed by `3 (latest: the gateway cuts at 30s, not 60)`, after the NOW fields and before the `Path:` line

#### Scenario: No linked notes
- **WHEN** no note links to `INIT-0009` and the user runs `wcm resume INIT-0009`
- **THEN** the brief contains no `Notes:` line

#### Scenario: Notes shown when resuming the active one again
- **WHEN** `INIT-0007` is active, one valid note links to it, and the user runs `wcm resume`
- **THEN** the brief contains `Notes:` followed by `1 (latest: <its title>)`, and no file is written

#### Scenario: Free and malformed notes are not counted
- **WHEN** one valid note links to `INIT-0007`, one free note exists, and a malformed note file contains `[[INIT-0007]]`, and the user runs `wcm resume INIT-0007`
- **THEN** the brief contains `Notes:` followed by `1 (latest: <title of the valid note>)`
