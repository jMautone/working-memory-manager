# Spec Delta

## Purpose

Lets a person save something worth keeping in under five seconds without letting go of the current initiative, and find it again weeks later without remembering where it was saved. A note is one plain Markdown file in the `work` knowledge base, named by its ID, linked to the initiative that was active when it was saved.

## ADDED Requirements

### Requirement: Note file format
Each note SHALL be a file `notes/<ID>.md` in the `work` knowledge base, where `<ID>` is `NOTE-` followed by at least four zero-padded digits. The file SHALL consist of a YAML frontmatter block delimited by `---` lines followed by a Markdown body. A note written by the system SHALL have, in this order, the frontmatter keys `id`, `title`, `tags`, `initiative`, `capture`, `created` and `updated`, and a body that begins with a level-one heading holding the title (`# <title>`). `tags` SHALL be a list, written as `[]` when empty. `initiative` SHALL be the link `[[<initiative ID>]]` written as a quoted string, or `null`. `capture` SHALL be `null`. Timestamps SHALL be ISO 8601 with a UTC offset. The file SHALL be UTF-8 without a byte-order mark, with `\n` line endings on every OS.

#### Scenario: File written on save
- **WHEN** no initiative is active, the highest note ID is `NOTE-0011`, and the user runs `wcm note "the gateway cuts at 30s, not 60" -t infra`
- **THEN** `notes/NOTE-0012.md` exists, its frontmatter holds `id: NOTE-0012`, `title: the gateway cuts at 30s, not 60`, `tags` with the single entry `infra`, `initiative: null`, `capture: null`, and `created` and `updated` set to the same timestamp with offset, and its body is the line `# the gateway cuts at 30s, not 60` with nothing after it

#### Scenario: Linked note frontmatter
- **WHEN** `INIT-0007` is active and the user runs `wcm note "retry budget is 3"`
- **THEN** the note's `initiative` value is the text `[[INIT-0007]]`, quoted, so that YAML reads it as a string and Obsidian resolves it as a link

### Requirement: Save a note
`wcm note <text...>` SHALL create a note whose title is the given words joined by single spaces, collapsed to one line, and SHALL NOT open an editor or prompt. Options SHALL be accepted before or after the text. On success the command SHALL print `<ID> saved.` (or the linked form, see "Notes link to the active initiative") and exit with code 0. Text made only of whitespace SHALL be refused with exit code 2 and nothing written. The command SHALL never overwrite an existing file.

#### Scenario: Save without opening anything
- **WHEN** no initiative is active and the user runs `wcm note el gateway corta a los 30s`
- **THEN** a note titled `el gateway corta a los 30s` is created, no prompt or editor appears, the output is `NOTE-0001 saved.` and the exit code is 0

#### Scenario: Options after the text
- **WHEN** the user runs `wcm note "retry budget is 3" -t payments --free`
- **THEN** the note is created with the tag `payments` and `initiative: null`

#### Scenario: Blank text refused
- **WHEN** the user runs `wcm note "   "`
- **THEN** the command exits with code 2, says a text is required, and no file is created under `notes/`

### Requirement: Note text from a prompt
When `wcm note` receives no text and stdin is a terminal, it SHALL print a `Note` prompt, read one line itself, and save that line as the title. An empty answer SHALL save nothing, say so and exit with code 1. When `wcm note` receives no text and stdin is not a terminal, it SHALL NOT read stdin; it SHALL exit with code 2, say a text is required, and write nothing.

#### Scenario: Text typed at the prompt
- **WHEN** stdin is a terminal and the user runs `wcm note -t infra` and types `gateway: #retries; at the edge`
- **THEN** a note titled `gateway: #retries; at the edge` with the tag `infra` is created and the exit code is 0

#### Scenario: Empty answer saves nothing
- **WHEN** stdin is a terminal, the user runs `wcm note` and presses Enter without typing
- **THEN** no file is created under `notes/`, the output says nothing was saved, and the exit code is 1

#### Scenario: No text and no terminal
- **WHEN** the user runs `wcm note` with stdin redirected from a file that contains a line of text
- **THEN** the command exits with code 2, says a text is required, no file is created, and the content of the file is not used

### Requirement: Tags on a note
`-t/--tag <tag>` on `wcm note` SHALL add tags to the note. The option SHALL be repeatable and each value SHALL also be split on commas. Each tag SHALL be trimmed, a single leading `#` SHALL be removed, empty tags SHALL be dropped, and a tag repeated case-insensitively SHALL be kept once, in its first spelling, keeping the order given.

#### Scenario: Repeated and comma-separated tags
- **WHEN** the user runs `wcm note "x" -t infra -t "db, Infra" -t "#gateway"`
- **THEN** the note's `tags` are `infra`, `db` and `gateway`, in that order

### Requirement: Notes link to the active initiative
When an initiative is active and `--free` is not given, `wcm note` SHALL write `initiative: "[[<ID>]]"` with the active initiative's ID and print `<note ID> saved, linked to <initiative ID> <initiative title>.` With `--free`, or when no initiative is active, `initiative` SHALL be `null` and the output SHALL be `<note ID> saved.` When more than one initiative is active on disk, the command SHALL save the note with `initiative: null`, print a line starting with `!` that names the active initiatives and says the note was not linked, and exit with code 0. The command SHALL NOT change any initiative file.

#### Scenario: Linked to the active initiative
- **WHEN** `INIT-0007` "Payment retries" is active and the user runs `wcm note "the gateway cuts at 30s, not 60"`
- **THEN** the output is `NOTE-0012 saved, linked to INIT-0007 Payment retries.` and `INIT-0007.md` is byte-for-byte unchanged

#### Scenario: Free note
- **WHEN** `INIT-0007` is active and the user runs `wcm note "Thinking in Systems: stocks and flows" --free`
- **THEN** the note has `initiative: null` and the output is `NOTE-0013 saved.`

#### Scenario: Two active initiatives on disk
- **WHEN** `INIT-0003` and `INIT-0004` both have `status: active` and the user runs `wcm note "x"`
- **THEN** the note is saved with `initiative: null`, a `!` line names `INIT-0003` and `INIT-0004` and says the note was not linked, and the exit code is 0

### Requirement: Edit a note
`wcm note edit <ID>` SHALL open the note file in the editor (see "Editor selection") and wait for the editor to exit. `wcm note -e <text...>` SHALL save the note as `wcm note` would, print its saved line, and then open it the same way. After the editor exits with code 0, the command SHALL print `<ID> updated.` when the file changed and `<ID> unchanged.` otherwise. `edit` SHALL be recognized only as the first argument of `wcm note`; it SHALL then require exactly one more argument, a note ID, SHALL NOT be combined with `-t`, `-e` or `--free`, and otherwise exit with code 2. `wcm note edit` SHALL open a note even if it is malformed, since editing is how it gets fixed. An unknown note ID SHALL exit with code 1 saying the ID was not found.

#### Scenario: Write the body later
- **WHEN** `NOTE-0012` exists and the user runs `wcm note edit 12`, adds a paragraph in the editor and saves
- **THEN** the paragraph is in `notes/NOTE-0012.md`, the output is `NOTE-0012 updated.` and the exit code is 0

#### Scenario: Write the body now
- **WHEN** the user runs `wcm note -e "retry budget"` and adds a paragraph in the editor
- **THEN** the output shows `NOTE-0014 saved.` before the editor opens and `NOTE-0014 updated.` after it closes, and the file holds the paragraph

#### Scenario: Editor closed without changes
- **WHEN** the user runs `wcm note edit 12` and closes the editor without saving
- **THEN** the output is `NOTE-0012 unchanged.`, the file is byte-for-byte unchanged and the exit code is 0

#### Scenario: Fix a malformed note
- **WHEN** `notes/NOTE-0005.md` has unbalanced quotes in its frontmatter and the user runs `wcm note edit 5`
- **THEN** the editor opens that file

#### Scenario: Unknown note
- **WHEN** no `notes/NOTE-0099.md` exists and the user runs `wcm note edit 99`
- **THEN** the command exits with code 1, says `NOTE-0099` was not found, and no editor opens

#### Scenario: Edit without an ID
- **WHEN** the user runs `wcm note edit`
- **THEN** the command exits with code 2, says a note ID is required, and nothing is created

#### Scenario: A note that starts with the word edit
- **WHEN** the user runs `wcm note "edit the config before deploying"`
- **THEN** a note titled `edit the config before deploying` is created

### Requirement: Editor selection
The editor SHALL be the command in the environment variable `VISUAL` when it is set and not blank, otherwise the one in `EDITOR`, otherwise the OS default. The value SHALL be split into a program and its arguments, where double quotes group a program path or an argument that contains spaces; the note's absolute path SHALL be appended as the last argument. The editor SHALL run attached to the same console as the CLI. If the editor cannot be started, the command SHALL exit with code 1 naming the command it tried and suggesting `VISUAL` or `EDITOR`. If the editor exits with a non-zero code, the command SHALL exit with code 1, report that code, and leave the file exactly as it is on disk. In both cases a note just saved by `wcm note -e` SHALL remain saved.

#### Scenario: Default editor (Windows)
- **WHEN** neither `VISUAL` nor `EDITOR` is set on Windows and the user runs `wcm note edit 12`
- **THEN** the note opens in `notepad` and the command waits until that window closes

#### Scenario: Default editor (macOS and Linux)
- **WHEN** neither `VISUAL` nor `EDITOR` is set on macOS or Linux and the user runs `wcm note edit 12`
- **THEN** the note opens in `vi` in the same terminal

#### Scenario: Editor with arguments
- **WHEN** `EDITOR` is `code --wait` and `VISUAL` is not set
- **THEN** `wcm note edit 12` runs `code` with the arguments `--wait` and the absolute path of `notes/NOTE-0012.md`

#### Scenario: VISUAL wins over EDITOR
- **WHEN** `VISUAL` and `EDITOR` name different editors
- **THEN** `wcm note edit 12` opens the one in `VISUAL`

#### Scenario: Editor cannot start
- **WHEN** `EDITOR` names a program that does not exist and the user runs `wcm note -e "x"`
- **THEN** the output shows the note as saved, the command exits with code 1 naming that program and suggesting `VISUAL` or `EDITOR`, and the note file exists

#### Scenario: Editor fails
- **WHEN** the editor exits with code 3 after changing the file
- **THEN** the command exits with code 1 and reports code 3, and the file is left as the editor wrote it, without a new `updated` value

### Requirement: Updated follows edits
After the editor exits with code 0, when the note file changed and still reads as a valid note, the system SHALL set `updated` to the current time by changing only that value in the frontmatter; every other byte SHALL remain as the editor left it. When the frontmatter has no `updated` key, the system SHALL add it as the last frontmatter line. When the file did not change, the system SHALL NOT write it. When the file changed but no longer reads as a valid note, the system SHALL NOT write it, and the command SHALL exit with code 1 naming the file and the reason.

#### Scenario: Edit refreshes updated
- **WHEN** `NOTE-0012` was created yesterday and the user adds a line with `wcm note edit 12`
- **THEN** `updated` is now, `created` is unchanged, and every other line is exactly as the editor saved it

#### Scenario: Hand formatting preserved
- **WHEN** the user writes a YAML comment and a flow list `tags: [infra, db]` in the frontmatter during `wcm note edit 12`
- **THEN** after the command both are still in the file exactly as written

#### Scenario: Edit breaks the note
- **WHEN** the user deletes the `id` line during `wcm note edit 12`
- **THEN** the command exits with code 1 naming `notes/NOTE-0012.md` and saying it has no id, and the file is exactly as the editor left it

### Requirement: Find notes
`wcm notes [term...]` SHALL list the valid notes of the `work` knowledge base that match every given filter, one line per note, most recently created first; notes with the same or no `created` value SHALL follow by ID, highest first, with notes without `created` last. Each term SHALL match, case-insensitively, as a substring of the title, of any tag, or of the body (the Markdown after the frontmatter); each term is matched on its own, so different terms can match different fields. A term with spaces, given as one argument, SHALL match as one substring. Accents SHALL NOT be ignored. `-t/--tag <tag>`, repeatable and comma-separated, SHALL keep only notes that have every given tag, compared case-insensitively and ignoring a leading `#`. `-i/--initiative <ID>` SHALL keep only notes linked to that initiative and SHALL accept the initiative ID forms `INIT-0007`, `init-7` and `7`. The command SHALL NOT modify any file and SHALL produce the same output from any directory.

#### Scenario: Search by a word
- **WHEN** `NOTE-0012` is titled `the gateway cuts at 30s, not 60`, `NOTE-0004` has `Gateway` only in its body, `NOTE-0009` mentions neither, and the user runs `wcm notes gateway`
- **THEN** the output lists `NOTE-0012` and `NOTE-0004` in order of creation, newest first, and not `NOTE-0009`

#### Scenario: Several terms must all match
- **WHEN** `NOTE-0012` contains `gateway` and `timeout`, `NOTE-0004` contains only `gateway`, and the user runs `wcm notes gateway timeout`
- **THEN** only `NOTE-0012` is listed

#### Scenario: Match in a tag
- **WHEN** `NOTE-0003` has the tag `infra` and the word appears nowhere else, and the user runs `wcm notes INFRA`
- **THEN** `NOTE-0003` is listed

#### Scenario: Accents are significant
- **WHEN** the only note mentioning a version spells it `versión` and the user runs `wcm notes version`
- **THEN** that note is not listed

#### Scenario: Filter by tag and initiative
- **WHEN** `INIT-0007` exists, `NOTE-0012` has the tag `infra` and links to `INIT-0007`, `NOTE-0013` has the tag `infra` and is free, and the user runs `wcm notes -t infra -i 7`
- **THEN** only `NOTE-0012` is listed

#### Scenario: Unknown initiative filter
- **WHEN** no initiative `INIT-0099` exists under `initiatives/` or `done/` and the user runs `wcm notes -i 99`
- **THEN** the command exits with code 1 and says `INIT-0099` was not found

#### Scenario: Invalid initiative filter
- **WHEN** the user runs `wcm notes -i abc`
- **THEN** the command exits with code 2

#### Scenario: Nothing matches
- **WHEN** notes exist and none contains `kubernetes`, and the user runs `wcm notes kubernetes`
- **THEN** the output is one line saying no notes match and the exit code is 0

#### Scenario: No notes yet
- **WHEN** there are no notes and the user runs `wcm notes`
- **THEN** the output is one line mentioning `wcm note` and the exit code is 0

#### Scenario: List all without terms
- **WHEN** three valid notes exist and the user runs `wcm notes`
- **THEN** all three are listed, newest first

### Requirement: One line per found note
Each note listed by `wcm notes` SHALL occupy exactly one line holding, in order: its ID, its title, its age since `created` rendered as in `wcm now` (`23m`, `1h 23m`, `2d`, `3w`, or `?` when `created` is missing or unreadable), and the ID of the initiative it links to, when it links to one. When the line would be wider than the terminal (or 100 columns when the width is unknown), the title SHALL be shortened with an ellipsis so the line fits; the ID, the age and the initiative ID SHALL NOT be cut.

#### Scenario: Linked note line
- **WHEN** `NOTE-0012`, titled `the gateway cuts at 30s, not 60`, was created two hours ago and links to `INIT-0007`
- **THEN** its line contains, in order, `NOTE-0012`, the title, `2h` and `INIT-0007`

#### Scenario: Free note line
- **WHEN** `NOTE-0004` is free and was created three weeks ago
- **THEN** its line contains `NOTE-0004`, its title and `3w`, and no initiative ID

#### Scenario: Long title is shortened
- **WHEN** a note's title is 300 characters long and the terminal is 80 columns wide
- **THEN** its line is at most 80 columns, the title ends with `…`, and the line still ends with its age (and initiative ID, if linked)

### Requirement: Note links are read from the initiative field
A note SHALL be linked to an initiative when its `initiative` value is `[[<initiative ID>]]`, optionally with `|<alias>` before the closing brackets, or the bare initiative ID, with the ID in its canonical form compared case-insensitively. Any other value, including `null`, SHALL make the note free. A note written by hand with a link SHALL be counted and filtered like one the system wrote.

#### Scenario: Link with an alias
- **WHEN** `INIT-0007` exists, a note has `initiative: "[[INIT-0007|payment retries]]"` and the user runs `wcm notes -i 7`
- **THEN** that note is listed

#### Scenario: Unrecognized value is free
- **WHEN** `INIT-0007` exists and a note has `initiative: payment retries`
- **THEN** `wcm notes` lists it without an initiative ID and `wcm notes -i 7` does not list it

### Requirement: Note IDs
The next note ID SHALL be one greater than the highest number among file names in `notes/` that match `NOTE-<digits>.md`, or `NOTE-0001` when there is none. The system SHALL NOT keep a counter file. IDs SHALL never be reused, even when lower-numbered notes have been deleted, and a malformed note still counts. Commands SHALL accept a note ID case-insensitively as `NOTE-0012`, as `note-12` (prefix with an unpadded number) or as the bare number `12`; any other form SHALL be a usage error with exit code 2.

#### Scenario: First note
- **WHEN** `notes/` does not exist and the user runs `wcm note "first"`
- **THEN** `notes/NOTE-0001.md` is created

#### Scenario: Gap is not reused
- **WHEN** `notes/` holds `NOTE-0003.md` and `NOTE-0007.md` and the user runs `wcm note "next"`
- **THEN** the note receives `NOTE-0008`

#### Scenario: Malformed note still counts
- **WHEN** the highest-numbered file is `notes/NOTE-0009.md` and it cannot be parsed, and the user runs `wcm note "next"`
- **THEN** the note receives `NOTE-0010` and `NOTE-0009.md` is unchanged

#### Scenario: Short forms accepted
- **WHEN** `NOTE-0012` exists and the user runs `wcm note edit 12`, `wcm note edit note-12` or `wcm note edit NOTE-0012`
- **THEN** each command opens `notes/NOTE-0012.md`

#### Scenario: Invalid note ID
- **WHEN** the user runs `wcm note edit twelve`
- **THEN** the command exits with code 2 and no editor opens

### Requirement: Hand-written notes are recognized
A file `notes/NOTE-<digits>.md` written by hand SHALL be read as a note when its frontmatter is a YAML mapping with an `id` equal to its file name and a title. The title SHALL come from the `title` key, or, when that is missing or empty, from the first level-one heading of the body. Every other key is optional: `tags` written as a single text value SHALL be read as one tag, and unknown keys SHALL be ignored and preserved.

#### Scenario: Minimal hand-written note
- **WHEN** the user creates `notes/NOTE-0020.md` by hand with a frontmatter holding only `id: NOTE-0020` and a body `# Idempotency keys` followed by a paragraph
- **THEN** `wcm notes idempotency` lists `NOTE-0020` with the title `Idempotency keys` and `?` as its age

### Requirement: Malformed notes are reported, never fixed
A file named `notes/NOTE-<digits>.md` SHALL be malformed when it has no frontmatter, its frontmatter is not valid YAML or not a mapping, it has no `id`, its `id` differs from its file name, or it has no title. `wcm notes` SHALL list the valid notes, then print one line starting with `!`, naming the file and the reason, per malformed file that could match: one whose raw text contains, case-insensitively, every given term, every given tag without its leading `#`, and the ID of the given initiative. With no filters, that is every malformed file. The command SHALL exit with code 0. Malformed notes SHALL never match a search, be counted in a resume brief, or be rewritten by the system.

#### Scenario: Broken note during a search
- **WHEN** `NOTE-0005` mentions `gateway` and has unbalanced quotes in its frontmatter, `NOTE-0012` contains `gateway`, and the user runs `wcm notes gateway`
- **THEN** `NOTE-0012` is listed, a `!` line names `notes/NOTE-0005.md`, `NOTE-0005.md` is unchanged and the exit code is 0

#### Scenario: Broken note that cannot match
- **WHEN** `NOTE-0005` has unbalanced quotes in its frontmatter and does not contain `kubernetes` anywhere, and the user runs `wcm notes kubernetes`
- **THEN** no `!` line names `notes/NOTE-0005.md`; `wcm notes` with no filters still names it

#### Scenario: Name and id disagree
- **WHEN** `notes/NOTE-0006.md` holds `id: NOTE-0016` and the user runs `wcm notes`
- **THEN** a `!` line names `notes/NOTE-0006.md` as malformed and neither `NOTE-0006` nor `NOTE-0016` is listed
