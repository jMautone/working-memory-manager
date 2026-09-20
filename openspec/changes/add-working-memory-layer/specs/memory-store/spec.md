## Purpose

Defines where and how WCM persists initiatives, checkpoints and captures as plain text that a person can read, edit by hand, and rebuild without the tool. Identity comes from the files themselves, never from a counter that can drift.

## ADDED Requirements

### Requirement: Storage root outside any repository
The system SHALL keep all memory under a single root directory that defaults to `~/.wcm` and never under the current working directory or a code repository. The environment variable `WCM_HOME` SHALL override the root when set. The root and its subdirectories SHALL be created on first write.

#### Scenario: Default root
- **WHEN** `WCM_HOME` is not set and the user runs `wcm new "Payment retries"`
- **THEN** the initiative is written under `~/.wcm/initiatives/`

#### Scenario: Root override
- **WHEN** `WCM_HOME` is set to `C:\tmp\wcm-test` and the user runs `wcm new "Payment retries"`
- **THEN** the initiative is written under `C:\tmp\wcm-test\initiatives\` and `~/.wcm` is not touched

#### Scenario: Current directory is irrelevant
- **WHEN** the user runs any `wcm` command from inside a Git repository
- **THEN** no file is created or modified inside that repository

### Requirement: Storage layout
The system SHALL use this layout under the root:

```text
initiatives/<ID>-<slug>/initiative.md
initiatives/<ID>-<slug>/checkpoints/<timestamp>.md
done/<ID>-<slug>/...           (closed initiatives, same inner layout)
inbox.md                       (one capture per line)
```

`<ID>` is `INIT-` followed by four zero-padded digits. `<slug>` is derived from the title (lowercase, ASCII letters, digits and hyphens, at most 40 characters) and is cosmetic.

#### Scenario: New initiative directory
- **WHEN** the user runs `wcm new "Payment retries"` and the highest existing ID is `INIT-0006`
- **THEN** `initiatives/INIT-0007-payment-retries/initiative.md` exists and `initiatives/INIT-0007-payment-retries/checkpoints/` exists as an empty directory

#### Scenario: Closed initiative moves to done
- **WHEN** the user runs `wcm done INIT-0007`
- **THEN** the directory `initiatives/INIT-0007-payment-retries/` no longer exists and `done/INIT-0007-payment-retries/initiative.md` exists with all of its checkpoints

### Requirement: Initiative file format
Each `initiative.md` SHALL consist of a YAML frontmatter block delimited by `---` lines followed by a Markdown body that begins with a `# NOW` heading. The frontmatter SHALL contain at least: `id`, `title`, `type`, `status`, `priority`, `created`, `updated`, `last_resumed`, `last_paused`, `waiting_on`, `tags`, `path`, `links`. Two further fields are conditional: `closed` SHALL be present on a `done` initiative, and `capture` SHALL be present on an initiative created by `wcm promote`, holding the originating `CAP-<NNNN>` ID. Timestamps SHALL be ISO 8601 with a UTC offset. Absent values SHALL be written as `null`.

#### Scenario: Frontmatter written on creation
- **WHEN** the user runs `wcm new "Payment retries" --type feature --priority high --path C:\wt\payment-retries`
- **THEN** the file's frontmatter contains `id: INIT-0007`, `title: Payment retries`, `type: feature`, `status: active`, `priority: high`, `path: C:\wt\payment-retries`, a `created` timestamp with offset, `last_paused: null` and `waiting_on: null`

#### Scenario: Body starts with NOW
- **WHEN** an initiative file is written by any command
- **THEN** the first non-blank line after the closing `---` is `# NOW`

### Requirement: The updated timestamp tracks writes
The system SHALL set `updated` to the current time whenever it rewrites an `initiative.md`, and SHALL NOT touch it otherwise. Read-only commands (`now`, `list`, `show`, `inbox`) and commands acting on a different initiative SHALL leave it unchanged. `created` SHALL never change after creation.

#### Scenario: Pause refreshes updated
- **WHEN** `INIT-0007` is paused with `wcm pause -n "Finish backoff"`
- **THEN** its `updated` timestamp is now and its `created` timestamp is unchanged

#### Scenario: Reading does not touch updated
- **WHEN** the user runs `wcm show INIT-0007` and then `wcm now`
- **THEN** `INIT-0007`'s `updated` timestamp is unchanged

### Requirement: Hand edits survive rewrites
When the system rewrites an `initiative.md`, it SHALL preserve frontmatter keys it does not know and SHALL preserve all body content that follows the NOW block. Only the known frontmatter fields and the NOW block are regenerated.

#### Scenario: Unknown key preserved
- **WHEN** the user adds `owner: ana` to the frontmatter by hand and then runs `wcm pause -n "Finish backoff"`
- **THEN** the rewritten file still contains `owner: ana`

#### Scenario: Notes below NOW preserved
- **WHEN** the user appends a `## Notes` section with three paragraphs after the NOW block and then runs `wcm pause -n "Finish backoff"`
- **THEN** the rewritten file still contains the `## Notes` section and its paragraphs unchanged, after the regenerated NOW block

### Requirement: Identity is the ID, the slug is cosmetic
The system SHALL identify an initiative by the `id` field in its frontmatter. Commands SHALL accept an ID as `INIT-0007`, case-insensitively, or as the bare number `7`. Renaming the slug part of the directory SHALL not affect any command.

#### Scenario: Bare number accepted
- **WHEN** the user runs `wcm show 7`
- **THEN** the output is the same as for `wcm show INIT-0007`

#### Scenario: Slug renamed by hand
- **WHEN** the user renames `INIT-0007-payment-retries` to `INIT-0007-retries` and runs `wcm show INIT-0007`
- **THEN** the initiative is found and displayed

### Requirement: Derived IDs without a counter
The next initiative ID SHALL be one greater than the highest ID found by scanning directory names under `initiatives/` and `done/`. The system SHALL NOT keep a counter file. IDs SHALL never be reused, even when lower-numbered directories have been deleted.

#### Scenario: Empty store
- **WHEN** the store has no initiatives and the user runs `wcm new "First"`
- **THEN** the initiative receives `INIT-0001`

#### Scenario: Highest ID lives in done
- **WHEN** `initiatives/` holds `INIT-0003-*` and `done/` holds `INIT-0009-*` and the user runs `wcm new "Next"`
- **THEN** the initiative receives `INIT-0010`

#### Scenario: Gap is not reused
- **WHEN** `INIT-0004` has been deleted by hand, the highest remaining ID is `INIT-0006`, and the user runs `wcm new "Next"`
- **THEN** the initiative receives `INIT-0007`

### Requirement: Reconstructible without the tool
A directory under `initiatives/` whose `initiative.md` was written by hand and follows the file format SHALL be recognized like any other initiative.

#### Scenario: Hand-written initiative is listed
- **WHEN** the user creates `initiatives/INIT-0002-notes/initiative.md` by hand with valid frontmatter (`status: paused`) and a NOW block whose `Next` is filled
- **THEN** `wcm list` and `wcm now` show `INIT-0002` under PAUSED

### Requirement: Malformed files are reported, never silently fixed
When an `initiative.md` cannot be parsed, or its frontmatter lacks `id` or `status`, or its `status` is not one of the four states, listing commands (`now`, `list`) SHALL continue with the remaining initiatives and print a warning naming the file. Commands that target the malformed initiative SHALL fail with a message naming the file and exit non-zero. The system SHALL NOT rewrite a file it could not parse.

#### Scenario: Broken frontmatter during now
- **WHEN** `INIT-0005` has unbalanced quotes in its frontmatter and the user runs `wcm now`
- **THEN** the other initiatives are shown and a warning line names `INIT-0005-*/initiative.md`

#### Scenario: Targeting a broken initiative
- **WHEN** the user runs `wcm resume INIT-0005` on that same file
- **THEN** the command exits non-zero, names the file, and no other initiative changes state

### Requirement: Writes never leave a truncated file
The system SHALL write each `initiative.md` and `inbox.md` such that an interruption during the write leaves either the previous complete content or the new complete content, never a partial file.

#### Scenario: Interrupted rewrite
- **WHEN** the process is killed while rewriting an `initiative.md`
- **THEN** the file on disk is either the previous version or the new version in full
