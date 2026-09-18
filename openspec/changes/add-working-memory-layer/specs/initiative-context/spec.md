## Purpose

Defines the five-field NOW block that lets a person resume an initiative in seconds, the prompt flow that keeps it current at every pause, and the append-only checkpoints that record how the work got here.

## ADDED Requirements

### Requirement: NOW block has five fixed fields
The body of every `initiative.md` SHALL begin with a `# NOW` heading followed by exactly these fields, in this order, each on its own line as `**<Label>:** <text>`: `Focus`, `Stopped at`, `Why it matters`, `Important`, `Next`. All five lines SHALL always be present; an empty field is written with no text after the label. `Next` is the only field that is mandatory, and only while the initiative is `paused` or `waiting`.

#### Scenario: NOW written on creation
- **WHEN** the user runs `wcm new "Payment retries" --why "Provider may return the same transaction ID after a timeout"`
- **THEN** the body contains `# NOW`, `**Focus:** Payment retries`, `**Stopped at:**` with no text, `**Why it matters:** Provider may return the same transaction ID after a timeout`, `**Important:**` with no text and `**Next:**` with no text

#### Scenario: Focus defaults to the title
- **WHEN** the user runs `wcm new "Payment retries"` without `--focus`
- **THEN** the `Focus` field reads `Payment retries`

### Requirement: NOW is rewritten, never grown
Every pause SHALL replace the values of the NOW fields in place. The system SHALL NOT append entries, dates or history to the NOW block.

#### Scenario: Two pauses leave one NOW
- **WHEN** `INIT-0007` is paused with `-n "Finish backoff"` and later resumed and paused again with `-n "Verify duplicates"`
- **THEN** the file contains exactly one `# NOW` heading, `**Next:** Verify duplicates`, and no line containing `Finish backoff` inside the NOW block

### Requirement: Pause flow prompts with the previous value
When the pause flow runs interactively (stdin is a terminal and no field flag was given), it SHALL prompt for `Next action`, then `Stopped at`, then `Important`, in that order. Each prompt SHALL display the previous value in brackets. Pressing Enter SHALL keep the previous value. Typing text SHALL replace it. Typing a single `-` SHALL clear the field. The flow SHALL NOT prompt for `Focus` or `Why it matters`. On success the command SHALL print `Checkpoint saved.` and `Safe to switch context.`

#### Scenario: Three Enters is a valid pause
- **WHEN** `INIT-0007` is active with `Next: Finish backoff`, and the user runs `wcm pause` and presses Enter three times
- **THEN** all NOW fields keep their values, a checkpoint is written, and the output ends with `Safe to switch context.`

#### Scenario: Typed text replaces
- **WHEN** the user types `Verify duplicate handling` at the `Next action` prompt and Enter at the others
- **THEN** `Next` is `Verify duplicate handling` and the other fields are unchanged

#### Scenario: Dash clears a field
- **WHEN** the user types `-` at the `Important` prompt
- **THEN** `Important` is empty after the pause

#### Scenario: Next cannot be cleared
- **WHEN** the user types `-` at the `Next action` prompt
- **THEN** the command refuses with a message that a next action is required, the initiative keeps its state, and no checkpoint is written

### Requirement: Pause flow without prompts
The flags `-n/--next`, `-s/--stopped-at` and `-i/--important` SHALL set the corresponding field. If any of them is given, the flow SHALL NOT prompt; fields not given keep their previous values. When stdin is not a terminal and no flag is given, the flow SHALL keep all previous values without prompting; if `Next` would be empty it SHALL fail with a message.

#### Scenario: Urgent pause with a flag
- **WHEN** `INIT-0007` is active and the user runs `wcm pause -n "Finish backoff"`
- **THEN** no prompt is shown, `Next` is `Finish backoff`, `Stopped at` and `Important` are unchanged, and a checkpoint is written

#### Scenario: Piped stdin with a prior Next
- **WHEN** `INIT-0007` has `Next: Finish backoff` and `wcm pause` is run with stdin redirected from a file
- **THEN** the pause succeeds with all fields unchanged and no prompt text is printed

#### Scenario: Piped stdin without a Next
- **WHEN** `INIT-0007` has an empty `Next` and `wcm pause` is run with stdin redirected from a file
- **THEN** the command fails, says a next action is required and suggests `-n`, and `INIT-0007` stays active

### Requirement: Oversized NOW is flagged
When the NOW block (the lines from `# NOW` up to the next Markdown heading or end of file, excluding blank lines) exceeds 15 lines, `wcm now` and `wcm show` SHALL print a warning naming the initiative and saying NOW is being used as a history.

#### Scenario: Long NOW warns
- **WHEN** the user hand-edits `INIT-0007` so its NOW block has 20 non-blank lines and runs `wcm now`
- **THEN** a warning line names `INIT-0007` and mentions the NOW size

### Requirement: Every transition writes a checkpoint
Each `pause`, `resume` (for the initiative being paused), `wait`, `done` and `checkpoint` command SHALL create a new file under the initiative's `checkpoints/` directory named `<YYYY-MM-DD>T<HHMMSS>.md` in local time, adding a numeric suffix (`-2`, `-3`) if that name already exists. The file SHALL contain, in order: a `# Checkpoint <timestamp>` heading, `Author: human`, `Trigger: <pause | switch | wait | done | manual>`, and the sections `## Focus`, `## Completed since previous checkpoint`, `## Incomplete work`, `## Discoveries`, `## Open questions`, `## Next action`. The system SHALL fill `Focus` from `Focus`, `Incomplete work` from `Stopped at`, `Discoveries` from `Important` and `Next action` from `Next`; the remaining sections SHALL be left empty for hand editing.

#### Scenario: Checkpoint written on pause
- **WHEN** `INIT-0007` is active with `Stopped at: backoff incomplete` and the user runs `wcm pause -n "Finish backoff"`
- **THEN** a new file exists under `checkpoints/`, its second line is `Author: human`, its third line is `Trigger: pause`, `## Incomplete work` is followed by `backoff incomplete` and `## Next action` is followed by `Finish backoff`

#### Scenario: Two checkpoints in the same second
- **WHEN** two checkpoints are written for the same initiative within one second
- **THEN** both files exist and the second one carries a `-2` suffix

### Requirement: Checkpoints are append-only
The system SHALL never modify, rename or delete an existing checkpoint file. `wcm checkpoint [ID]` SHALL create a checkpoint with `Trigger: manual` from the current NOW block and print its path; with `--edit` it SHALL then open the new file in the editor.

#### Scenario: Earlier checkpoint untouched
- **WHEN** `INIT-0007` already has a checkpoint and the user runs `wcm checkpoint INIT-0007`
- **THEN** the earlier file's contents are byte-for-byte unchanged and a second file exists with `Trigger: manual`

### Requirement: Resume brief
`wcm resume <ID>` SHALL print, after any switch, a brief consisting of the ID and title, how long ago it was paused (or since when it was waiting, with what it waited on), then each non-empty NOW field in order (`Focus`, `Stopped at`, `Why it matters`, `Important`, `Next`), then `Path:` when a path is recorded. The brief SHALL NOT include checkpoints or history.

#### Scenario: Brief after two days
- **WHEN** `INIT-0007` was paused two days ago with all five fields filled and a path, and the user runs `wcm resume INIT-0007`
- **THEN** the output contains `INIT-0007`, `Payment retries`, `paused 2d ago`, the five field values and a `Path:` line

#### Scenario: Empty fields are skipped
- **WHEN** `INIT-0009` has empty `Stopped at` and `Important` fields
- **THEN** the brief printed by `wcm resume INIT-0009` contains no `Stopped at` or `Important` lines
