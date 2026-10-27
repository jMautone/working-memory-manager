# wcm

`wcm` is a working memory layer. It lets you interrupt any initiative, take it
out of your short-term memory, and pick it up hours, days or weeks later in
under 30 seconds, without rereading conversations.

Three operations are the core:

- **`wcm pause`** lets go of what you are doing: it asks for the next action
  (Enter keeps the previous value) and saves a checkpoint.
- **`wcm now`** shows, from any directory, what is active, what is paused and
  what needs attention.
- **`wcm resume`** switches to an initiative: it pauses the current one, shows
  where you stopped and what comes next, and takes your shell to the work.

Next to them, notes: **`wcm note`** saves something worth keeping in a few
seconds, linked to the active initiative, and **`wcm notes`** finds it again
weeks later.

Everything is plain Markdown and YAML in `~/.wcm`, outside any repository,
readable and editable by hand, and openable in Obsidian. The plan behind it is
[`persistent-working-memory-plan.md`](persistent-working-memory-plan.md).

## Install

Requires Python 3.14. On Windows, use the `py` launcher:

```powershell
git clone https://github.com/jMautone/working-memory-manager
py -3.14 -m pip install .\working-memory-manager
```

Then add the PowerShell module to your profile, so `wcm resume` can change
your shell's directory (a child process cannot do it on its own). A fresh
Windows account has no profile yet, and runs no scripts until you allow it:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # if scripts are disabled
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
Add-Content $PROFILE "`r`nImport-Module <path to working-memory-manager>\shell\wcm.psm1"
```

On a managed machine, Group Policy may override the execution policy.

Open a new PowerShell and run `wcm now`. The module finds the `wcm` command
pip installed, or falls back to `py -3.14 -m wcm` when pip's `Scripts`
directory is not on `PATH`. Without the module every command still works
(as `py -3.14 -m wcm <command>` if `wcm` is not on `PATH`), except the
automatic directory change.

On macOS and Linux, install into a virtual environment or with `pipx`, since
system and Homebrew Pythons refuse a plain `pip install`:

```sh
pipx install ./working-memory-manager
# or
python3.14 -m venv ~/.venvs/wcm && ~/.venvs/wcm/bin/pip install ./working-memory-manager
```

There is no shell wrapper for them yet: `resume` prints the path instead of
moving you there.

## Commands

```text
wcm new "<title>" [--type T] [--priority P] [--path DIR] [--tags a,b]
                  [--focus TEXT] [--why TEXT] [--next TEXT]
                  [--pause-next TEXT] [--paused]
wcm now
wcm pause  [ID] [-n NEXT] [-s STOPPED_AT] [-i IMPORTANT]
wcm resume [ID]
wcm done   [ID]
wcm note   [TEXT...] [-t TAG] [-e] [--free]
wcm note   edit ID
wcm notes  [TERM...] [-t TAG] [-i ID]
```

- **`new`** creates an initiative and makes it active, pausing the current
  one first. `--next` is the next action of the new initiative; `--pause-next`
  is the next action of the one being paused, so the switch needs no prompt.
  `--paused` creates it without switching (it then needs `--next`).
  `--path` records where the work happens; `resume` takes you there.
- **`now`** lists the ACTIVE and PAUSED initiatives, two lines each, then
  warnings starting with `!`: more than one active, a paused initiative
  without a next action, a missing path, an unreadable file, or an active
  initiative that has gone more than 4 hours without a checkpoint.
- **`pause`** asks for `Next action`, `Stopped at` and `Important`, showing
  the previous values: Enter keeps, text replaces, `-` clears. A next action
  is required. `-n`, `-s` and `-i` set the fields without prompting.
- **`resume ID`** pauses the active initiative (same prompts), activates the
  target and prints its brief. `resume` with no ID shows the active one again
  and takes you to its directory, without writing anything.
- **`done`** closes an initiative and moves it to `done/`.
- **`note`** and **`notes`** save and find notes; see [Notes](#notes).

IDs are accepted as `INIT-0007`, `init-7` or `7`. Without an ID, `pause` and
`done` act on the active initiative.

Exit codes: `0` success, `1` the command was refused (unknown ID, malformed
file, nothing active, a missing next action, an editor that failed), `2`
usage error.

## Notes

```sh
wcm note "the gateway cuts at 30s, not 60" -t infra
wcm note "Thinking in Systems: stocks and flows" --free
wcm note -e "retry budget"
wcm note edit 12
wcm notes gateway
wcm notes -t infra -i 7
```

- **`note TEXT`** saves a note whose title is the text, without opening
  anything, and prints `NOTE-0012 saved.` When an initiative is active the
  note links to it: `NOTE-0012 saved, linked to INIT-0007 Payment retries.`
  - `-t TAG` adds tags; repeat it or separate them with commas
    (`-t infra -t db`, `-t infra,db`). A leading `#` is dropped.
  - `--free` saves it without a link.
  - `-e` saves it, then opens it in your editor to write the body.
  - With no text, in a terminal, it asks for one line (`Note`).
- **`note edit ID`** opens a note in your editor, also a broken one, since
  that is how you fix it. When you close the editor it prints `updated` or
  `unchanged`. `edit` is only special as the first word: to save a note that
  starts with it, quote the whole text (`wcm note "edit the config"`).
- **`notes TERM...`** lists notes, newest first, one line each: ID, title,
  age and the initiative it links to. Each term must appear, ignoring case,
  in the title, a tag or the body; several terms must all appear, and a
  quoted term with spaces (`"gateway timeout"`) is one term. Accents count:
  `version` does not find `versión`. With no terms it lists every note.
  - `-t TAG` keeps notes with that tag (repeat or comma-separate: all must
    be there).
  - `-i ID` keeps notes linked to that initiative, open or done.

Note IDs are accepted as `NOTE-0012`, `note-12` or `12`.

When at least one note links to an initiative, the brief that `wcm resume`
prints shows how many and the latest:

```text
  Notes:          3 (latest: the gateway cuts at 30s, not 60)
```

### Typing a note in Windows PowerShell 5.1

PowerShell reads the arguments before `wcm` sees them: unquoted, a `#` at
the start of a word cuts off the rest of the line and `;` starts another
command; inside double quotes, `$name` is expanded. When the text has any of
those, run `wcm note` with no text (and your `-t` tags) and type it at the
prompt: `wcm` reads that line itself, exactly as typed.

`wcm note` never reads its text from a pipe, on any OS: piped through
Windows PowerShell 5.1, accents arrive as `?`.

### Editor

`wcm note -e` and `wcm note edit` open the editor in `VISUAL`, or else in
`EDITOR`, or else `notepad` on Windows and `vi` on macOS and Linux. The
command can carry arguments, and double quotes group a path with spaces:

```powershell
$env:EDITOR = "code --wait"
$env:EDITOR = '"C:\Program Files\Notepad++\notepad++.exe" -multiInst -nosession'
```

`wcm` waits for the editor to exit, so a graphical editor needs its "wait"
flag (`code --wait`). Without it, `wcm` sees no change, prints `unchanged`,
and the note's `updated` is set on the next edit.

## Storage

`WCM_HOME` overrides the location (default `~/.wcm`).

```text
~/.wcm/
  kbs/
    work/                              the "work" knowledge base
      initiatives/
        INIT-0007/
          INIT-0007.md                 frontmatter + title + NOW; rewritten
          checkpoints/
            2026-09-16T164000.md       append-only, one per pause
      done/
        INIT-0003/...                  closed initiatives, same layout
      notes/
        NOTE-0012.md                   one file per note, named by its ID
```

`kbs/work/` is a plain folder you can open as an Obsidian vault: files are
named by ID, so a link like `[[INIT-0007]]` resolves. `.obsidian/` and any
other file you keep there are ignored by `wcm`.

An initiative file looks like this:

```markdown
---
id: INIT-0007
title: Payment retries
type: feature
status: paused
priority: normal
created: 2026-09-10T09:12:00-03:00
updated: 2026-09-16T16:40:00-03:00
last_resumed: 2026-09-16T14:12:00-03:00
last_paused: 2026-09-16T16:40:00-03:00
waiting_on: null
tags:
- payments
workspaces:
- path: C:\wt\payment-retries
  primary: true
links: []
---

# Payment retries

## NOW

**Focus:** Retry policy for payment authorizations

**Stopped at:** Classification done; backoff incomplete

**Why it matters:** The provider may return the same transaction ID after a timeout

**Important:** Validate idempotency before enabling retries

**Next:** Finish PaymentRetryPolicy and verify duplicate handling
```

A note file looks like this:

```markdown
---
id: NOTE-0012
title: the gateway cuts at 30s, not 60
tags:
- infra
initiative: "[[INIT-0007]]"
capture: null
created: 2026-09-16T16:20:00-03:00
updated: 2026-09-16T16:20:00-03:00
---

# the gateway cuts at 30s, not 60

Measured with a slow upstream: the gateway returns 504 after 30 seconds.
```

`initiative` is an Obsidian link, so the note shows up in the initiative's
backlinks. A note is listed by `wcm notes` by its `created` time; `updated`
follows your edits through `wcm note edit`.

## Editing by hand

The files are yours. When `wcm` rewrites an initiative it regenerates the
frontmatter keys it knows, the title heading and the NOW block, and keeps:

- frontmatter keys it does not know (`owner: ana`), with their values as you
  wrote them: `9:30`, `0123` or `yes` stay text;
- anything you write before `## NOW`, and everything after the NOW block (a
  `## Notes` section, for example);
- extra lines inside the NOW block, which count toward its size.

The frontmatter is rewritten as YAML, so its comments and layout (flow lists
like `[a, b]`, quoting) are not kept, only its keys and values. If a file has
no `title`, the first `# ` heading becomes the title.

It never repairs a file. If a file cannot be read, or its `id` or `status` is
missing or wrong, `wcm now` names it with a `!` warning and commands that
target it refuse. Checkpoints are never modified.

Notes are never rewritten. After `wcm note edit`, the only change `wcm` makes
is the value of `updated`; comments, flow lists and line endings stay as you
saved them. A note you write by hand (in Obsidian, say) needs only a file
name like `NOTE-0020.md`, a frontmatter with `id: NOTE-0020`, and a title,
either as `title:` or as the first `# ` heading. To link it, set
`initiative: "[[INIT-0007]]"` (an alias such as `[[INIT-0007|retries]]` works
too). A note that cannot be read is named in a `!` line by `wcm notes` (in
a search, only when its text contains what you searched for). Other files in
`notes/` (`Gateway timeouts.md`, subfolders) are ignored.

Keep NOW small: five single-line fields. Over 15 lines, `wcm now` warns that
it is being used as a history.

To reopen a done initiative, move `kbs/work/done/INIT-0003/` back to
`kbs/work/initiatives/`, set `status: paused` and make sure it has a `Next`.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Checks:

```sh
py -3.14 -m pip install -e ".[dev]"
py -3.14 -m ruff check .
py -3.14 -m ruff format --check .
py -3.14 -m pytest tools
py -3.14 -m pytest
openspec validate --all --strict
```
