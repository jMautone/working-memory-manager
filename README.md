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

IDs are accepted as `INIT-0007`, `init-7` or `7`. Without an ID, `pause` and
`done` act on the active initiative.

Exit codes: `0` success, `1` the command was refused (unknown ID, malformed
file, nothing active, a missing next action), `2` usage error.

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
