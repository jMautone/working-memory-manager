## Purpose

Defines where and how WCM persists initiatives and checkpoints as plain text that a person can read, edit by hand, open as an Obsidian vault, and rebuild without the tool. Identity comes from the files themselves, never from a counter that can drift.

## ADDED Requirements

### Requirement: Storage root outside any repository
The system SHALL keep all memory under a single root directory, the hub, that defaults to `~/.wcm` and never under the current working directory or a code repository. The environment variable `WCM_HOME` SHALL override the hub when set. Initiatives and checkpoints SHALL live in the knowledge base `work`, at `<hub>/kbs/work/`. The hub, `kbs/work/` and their subdirectories SHALL be created on first write.

#### Scenario: Default root
- **WHEN** `WCM_HOME` is not set and the user runs `wcm new "Payment retries"`
- **THEN** the initiative is written under `~/.wcm/kbs/work/initiatives/`

#### Scenario: Root override
- **WHEN** `WCM_HOME` is set to a temporary directory and the user runs `wcm new "Payment retries"`
- **THEN** the initiative is written under `<that directory>/kbs/work/initiatives/` and `~/.wcm` is not touched

#### Scenario: Current directory is irrelevant
- **WHEN** the user runs any `wcm` command from inside a Git repository
- **THEN** no file is created or modified inside that repository

### Requirement: Storage layout
The system SHALL use this layout under `<hub>/kbs/work/`:

```text
initiatives/<ID>/<ID>.md
initiatives/<ID>/checkpoints/<timestamp>.md
done/<ID>/...                  (closed initiatives, same inner layout)
```

`<ID>` is `INIT-` followed by four zero-padded digits. The directory and the file are named by the ID alone; there is no slug.

#### Scenario: New initiative directory
- **WHEN** the user runs `wcm new "Payment retries"` and the highest existing ID is `INIT-0006`
- **THEN** `initiatives/INIT-0007/INIT-0007.md` exists and `initiatives/INIT-0007/checkpoints/` exists as an empty directory

#### Scenario: Closed initiative moves to done
- **WHEN** the user runs `wcm done INIT-0007`
- **THEN** the directory `initiatives/INIT-0007/` no longer exists and `done/INIT-0007/INIT-0007.md` exists with all of its checkpoints

### Requirement: Initiative file format
Each initiative file SHALL consist of a YAML frontmatter block delimited by `---` lines followed by a Markdown body. The body SHALL begin with a level-one heading holding the title (`# <title>`), followed by the NOW block under a `## NOW` heading. The frontmatter SHALL contain at least: `id`, `title`, `type`, `status`, `priority`, `created`, `updated`, `last_resumed`, `last_paused`, `waiting_on`, `tags`, `workspaces`, `links`. `workspaces` SHALL be a list whose entries hold `path` and `primary`; at most one entry is primary. `closed` SHALL be present on a `done` initiative. Timestamps SHALL be ISO 8601 with a UTC offset. Absent values SHALL be written as `null`, and an empty list as `[]`.

#### Scenario: Frontmatter written on creation
- **WHEN** the user runs `wcm new "Payment retries" --type feature --priority high --path <dir>`
- **THEN** the file's frontmatter contains `id: INIT-0007`, `title: Payment retries`, `type: feature`, `status: active`, `priority: high`, a `workspaces` list with one entry whose `path` is `<dir>` as an absolute path and whose `primary` is `true`, a `created` timestamp with offset, `last_paused: null` and `waiting_on: null`

#### Scenario: Creation without a path
- **WHEN** the user runs `wcm new "Research CRDTs"`
- **THEN** the frontmatter contains `workspaces: []`

#### Scenario: Body starts with the title
- **WHEN** an initiative titled `Payment retries` is written by any command
- **THEN** the first non-blank line after the closing `---` is `# Payment retries` and the next heading is `## NOW`

### Requirement: The updated timestamp tracks writes
The system SHALL set `updated` to the current time whenever it rewrites an initiative file, and SHALL NOT touch it otherwise. The read-only command `now` and commands acting on a different initiative SHALL leave it unchanged. `created` SHALL never change after creation.

#### Scenario: Pause refreshes updated
- **WHEN** `INIT-0007` is paused with `wcm pause -n "Finish backoff"`
- **THEN** its `updated` timestamp is now and its `created` timestamp is unchanged

#### Scenario: Reading does not touch updated
- **WHEN** the user runs `wcm now`
- **THEN** no initiative's `updated` timestamp changes

### Requirement: Hand edits survive rewrites
When the system rewrites an initiative file, it SHALL preserve frontmatter keys it does not know and SHALL preserve all body content that follows the NOW block. Only the known frontmatter fields, the title heading and the NOW block are regenerated.

#### Scenario: Unknown key preserved
- **WHEN** the user adds `owner: ana` to the frontmatter by hand and then runs `wcm pause -n "Finish backoff"`
- **THEN** the rewritten file still contains `owner: ana`

#### Scenario: Notes below NOW preserved
- **WHEN** the user appends a `## Notes` section with three paragraphs after the NOW block and then runs `wcm pause -n "Finish backoff"`
- **THEN** the rewritten file still contains the `## Notes` section and its paragraphs unchanged, after the regenerated NOW block

### Requirement: Identity is the ID
The system SHALL identify an initiative by the `id` field in its frontmatter. Commands SHALL accept an ID case-insensitively as `INIT-0007`, as `init-7` (prefix with an unpadded number) or as the bare number `7`. An initiative whose directory or file name differs from its `id` SHALL be reported as malformed.

#### Scenario: Short forms accepted
- **WHEN** `INIT-0007` is paused and the user runs `wcm resume 7`, or `wcm resume init-7`
- **THEN** each command resumes `INIT-0007`, exactly as `wcm resume INIT-0007` would

#### Scenario: Name and id disagree
- **WHEN** the file `initiatives/INIT-0007/INIT-0007.md` holds `id: INIT-0008` and the user runs `wcm now`
- **THEN** a warning line names the file as malformed and `INIT-0008` is not listed

### Requirement: Derived IDs without a counter
The next initiative ID SHALL be one greater than the highest ID found by scanning directory names under `initiatives/` and `done/` of the `work` knowledge base. The system SHALL NOT keep a counter file. IDs SHALL never be reused, even when lower-numbered directories have been deleted.

#### Scenario: Empty store
- **WHEN** the store has no initiatives and the user runs `wcm new "First"`
- **THEN** the initiative receives `INIT-0001`

#### Scenario: Highest ID lives in done
- **WHEN** `initiatives/` holds `INIT-0003` and `done/` holds `INIT-0009` and the user runs `wcm new "Next"`
- **THEN** the initiative receives `INIT-0010`

#### Scenario: Gap is not reused
- **WHEN** `INIT-0004` has been deleted by hand, the highest remaining ID is `INIT-0006`, and the user runs `wcm new "Next"`
- **THEN** the initiative receives `INIT-0007`

### Requirement: Reconstructible without the tool
A directory under `initiatives/` whose initiative file was written by hand and follows the file format SHALL be recognized like any other initiative.

#### Scenario: Hand-written initiative is listed
- **WHEN** the user creates `initiatives/INIT-0002/INIT-0002.md` by hand with valid frontmatter (`status: paused`) and a NOW block whose `Next` is filled
- **THEN** `wcm now` shows `INIT-0002` under PAUSED

### Requirement: Unrecognized files are ignored
The system SHALL ignore files and directories in the knowledge base that it does not own, including the `.obsidian/` directory that Obsidian creates in a vault. It SHALL never modify, move or delete them, and they SHALL NOT affect ID derivation.

#### Scenario: Obsidian settings present
- **WHEN** `kbs/work/.obsidian/` exists with files in it and `kbs/work/initiatives/README.md` exists, and the user runs `wcm now` and `wcm new "Next"`
- **THEN** neither command warns about those files, they are unchanged, and the new initiative's ID is derived only from initiative directories

### Requirement: Malformed files are reported, never silently fixed
When an initiative file cannot be parsed, or its frontmatter lacks `id` or `status`, or its `status` is not one of the four states, or its name does not match its `id`, the listing command `now` SHALL continue with the remaining initiatives and print a warning naming the file. Commands that target the malformed initiative SHALL fail with a message naming the file and exit with code 1. The system SHALL NOT rewrite a file it could not parse.

#### Scenario: Broken frontmatter during now
- **WHEN** `INIT-0005` has unbalanced quotes in its frontmatter and the user runs `wcm now`
- **THEN** the other initiatives are shown and a warning line names `INIT-0005/INIT-0005.md`

#### Scenario: Targeting a broken initiative
- **WHEN** the user runs `wcm resume INIT-0005` on that same file
- **THEN** the command exits with code 1, names the file, and no other initiative changes state

### Requirement: Writes never leave a truncated file
The system SHALL write each initiative file such that an interruption during the write leaves either the previous complete content or the new complete content, never a partial file.

#### Scenario: Interrupted rewrite
- **WHEN** the process is killed while rewriting an initiative file
- **THEN** the file on disk is either the previous version or the new version in full
