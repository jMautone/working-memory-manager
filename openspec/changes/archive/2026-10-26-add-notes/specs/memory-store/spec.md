# Spec Delta

## MODIFIED Requirements

### Requirement: Storage root outside any repository
The system SHALL keep all memory under a single root directory, the hub, that defaults to `~/.wcm` and never under the current working directory or a code repository. The environment variable `WCM_HOME` SHALL override the hub when set. Initiatives, checkpoints and notes SHALL live in the knowledge base `work`, at `<hub>/kbs/work/`. The hub, `kbs/work/` and their subdirectories SHALL be created on first write.

#### Scenario: Default root
- **WHEN** `WCM_HOME` is not set and the user runs `wcm new "Payment retries"`
- **THEN** the initiative is written under `~/.wcm/kbs/work/initiatives/`

#### Scenario: Root override
- **WHEN** `WCM_HOME` is set to a temporary directory and the user runs `wcm new "Payment retries"`
- **THEN** the initiative is written under `<that directory>/kbs/work/initiatives/` and `~/.wcm` is not touched

#### Scenario: Notes under the hub
- **WHEN** `WCM_HOME` is set to a temporary directory that does not exist yet and the user runs `wcm note "first"`
- **THEN** the note is written as `<that directory>/kbs/work/notes/NOTE-0001.md`, creating the missing directories

#### Scenario: Current directory is irrelevant
- **WHEN** the user runs any `wcm` command from inside a Git repository
- **THEN** no file is created or modified inside that repository

### Requirement: Storage layout
The system SHALL use this layout under `<hub>/kbs/work/`:

```text
initiatives/<ID>/<ID>.md
initiatives/<ID>/checkpoints/<timestamp>.md
done/<ID>/...                  (closed initiatives, same inner layout)
notes/<NOTE-ID>.md
```

`<ID>` is `INIT-` followed by four zero-padded digits; `<NOTE-ID>` is `NOTE-` followed by four zero-padded digits. Directories and files are named by the ID alone; there is no slug.

#### Scenario: New initiative directory
- **WHEN** the user runs `wcm new "Payment retries"` and the highest existing ID is `INIT-0006`
- **THEN** `initiatives/INIT-0007/INIT-0007.md` exists and `initiatives/INIT-0007/checkpoints/` exists as an empty directory

#### Scenario: Closed initiative moves to done
- **WHEN** the user runs `wcm done INIT-0007`
- **THEN** the directory `initiatives/INIT-0007/` no longer exists and `done/INIT-0007/INIT-0007.md` exists with all of its checkpoints

#### Scenario: New note file
- **WHEN** the user runs `wcm note "retry budget is 3"` and the highest existing note ID is `NOTE-0011`
- **THEN** `notes/NOTE-0012.md` exists and no other file or directory is created for it

#### Scenario: Closing an initiative leaves its notes in place
- **WHEN** `NOTE-0012` links to `INIT-0007` and the user runs `wcm done INIT-0007`
- **THEN** `notes/NOTE-0012.md` is unchanged and still links to `INIT-0007`

### Requirement: Unrecognized files are ignored
The system SHALL ignore files and directories in the knowledge base that it does not own, including the `.obsidian/` directory that Obsidian creates in a vault, files in `notes/` whose names do not match `NOTE-<digits>.md`, and subdirectories of `notes/`. It SHALL never modify, move or delete them, and they SHALL NOT affect ID derivation or appear in any listing.

#### Scenario: Obsidian settings present
- **WHEN** `kbs/work/.obsidian/` exists with files in it and `kbs/work/initiatives/README.md` exists, and the user runs `wcm now` and `wcm new "Next"`
- **THEN** neither command warns about those files, they are unchanged, and the new initiative's ID is derived only from initiative directories

#### Scenario: Other Markdown files in notes
- **WHEN** `notes/Gateway timeouts.md`, `notes/NOTE-12-draft.md` and `notes/archive/NOTE-0050.md` exist, the highest valid note is `NOTE-0012`, and the user runs `wcm notes` and `wcm note "next"`
- **THEN** none of those files is listed or warned about, they are unchanged, and the new note receives `NOTE-0013`

### Requirement: Writes never leave a truncated file
The system SHALL write each initiative file and each note file such that an interruption during the write leaves either the previous complete content or the new complete content, never a partial file. A new note file SHALL never replace an existing file.

#### Scenario: Interrupted rewrite
- **WHEN** the process is killed while rewriting an initiative file
- **THEN** the file on disk is either the previous version or the new version in full

#### Scenario: Interrupted note update
- **WHEN** the process is killed while setting `updated` on a note after an edit
- **THEN** the note file on disk is either the version the editor saved or that version with the new `updated` value, in full
