## Context

See proposal.md for motivation and scope. The repository holds the plan (`persistent-working-memory-plan.md`), the decisions in `docs/decisions/` (0001 for versions and releases, 0002 for notes, knowledge bases and the split of Phase 1), the CI and release tooling, and no product code. This change is the core of Phase 1: `new`, `now`, `pause`, `resume`, `done`, the store and the PowerShell wrapper. Its layout is the one ADR 0002 fixes, so that the following changes (`add-notes`, `add-inbox`, `add-knowledge-bases`, `add-initiative-tools`) add files and commands without breaking the format.

Environment facts that shape the approach (observed on the target machine):

- Python 3.14 is installed via the Windows launcher (`py -3.14`). The `python` on `PATH` is the Microsoft Store alias, not that interpreter.
- No YAML or frontmatter packages are installed. `pip` availability on this corporate machine is unverified.
- Shell is Windows PowerShell 5.1 (no `&&`, no ternary). The wrapper must run there.
- No Node dependency is acceptable for the tool itself.

The requirements themselves live in the five delta specs under `specs/`; this document does not restate them.

## Goals / Non-Goals

**Goals:**

- A `wcm now` that starts and renders in well under a second on a store of ~20 initiatives, because it is the most-run command.
- Every file the tool writes is something a person would write by hand, and opens cleanly in Obsidian: no generated indexes, no hidden state, no counters.
- Tests exercise every command end to end against a temporary store, including the interactive pause flow and the Phase 1 exit sequence.
- The PowerShell wrapper is thin enough to be read in one screen and never needs to parse CLI output.

**Non-Goals:**

- Anything the proposal lists as a non-goal.
- Colour or rich terminal UI. Plain text first; colour can be layered later without touching behaviour.
- Cross-platform shell wrappers. Only PowerShell ships; the CD protocol is shell-agnostic so bash/zsh wrappers can be added later.
- Locking for concurrent writers. One person, one machine, sequential commands.

## Decisions

### D1. Python 3.14 with `argparse`, no CLI framework

`argparse` from the standard library builds the subcommand tree (`new`, `now`, `pause`, `resume`, `done`). Exit codes: `0` success, `1` domain error (unknown ID, invariant refused, malformed file, nothing to act on), `2` usage error (argparse default). Errors go to stderr.

*Alternative discarded:* `click`/`typer` add imports on every start of `wcm now` and a dependency to install.

### D2. PyYAML is the only runtime dependency

Frontmatter is loaded with a `SafeLoader` subclass whose implicit resolvers keep only null and `true`/`false`: every other plain scalar loads as text. YAML 1.1 would otherwise turn a hand-written `9:30` into 570, `0123` into 83 and `yes` into True, and write them back that way. It is written with a `SafeDumper` subclass, `sort_keys=False`, `allow_unicode=True` and no line width, so hand-added keys survive, key order stays readable and long values are never folded. Strings that look like ISO timestamps are written plain (`created: 2026-09-16T09:00:00-03:00`), as people write them and Obsidian reads them; since the loader keeps them as text, they round-trip unchanged. Any exception while loading the frontmatter, not only `YAMLError`, makes the file malformed, never a traceback. Comments and flow style in the frontmatter are not preserved; the README says so.

*Alternative discarded:* a hand-rolled parser for the flat subset the tool writes; the files are hand-editable and people will write flow lists, quotes and nested maps. If `pip install` proves blocked on the target machine, vendor PyYAML under `src/wcm/_vendor/` instead (recorded as a risk).

### D3. Package layout and entry points

```text
pyproject.toml            name "wcm", version "0.0.0.dev0" (stamped at release),
                          console script wcm = wcm.cli:main
src/wcm/__init__.py
src/wcm/__main__.py       python -m wcm -> cli.main
src/wcm/cli.py            argparse tree, one handler per command, exit codes
src/wcm/ids.py            ID parsing (INIT-0007, init-7, 7) and formatting
src/wcm/store.py          hub and KB paths (WCM_HOME), initiative discovery,
                          ID derivation, atomic write, done/ move
src/wcm/model.py          Initiative dataclass, states, priorities, workspaces,
                          file parse/render (frontmatter, title H1, NOW block),
                          invariant checks
src/wcm/checkpoint.py     checkpoint file naming and rendering
src/wcm/prompt.py         pause prompt flow (TTY detection, prefill, dash-to-clear)
src/wcm/render.py         now and resume output, humanised ages, truncation,
                          warnings (including the stale-active check)
src/wcm/shell.py          WCM_CD_FILE protocol
src/wcm/clock.py          now() in local time with offset; injectable for tests
shell/wcm.psm1            PowerShell wrapper
tests/                    pytest; every test points WCM_HOME at tmp_path
README.md                 install, profile line, storage format, hand-editing rules
```

Installed with `py -3.14 -m pip install -e .` so a `wcm` console script lands on `PATH`. The wrapper prefers that script (D9). `pyproject.toml` keeps `version = "0.0.0.dev0"` in `[project]`, as ADR 0001 requires; `ruff` and `pytest` are development dependencies.

### D4. Pure decisions and effects

The boundary is the store. `ids`, `model` (parse, render, invariants), `checkpoint` (naming and content), `render` (screens, ages, warnings) and the transition logic in `cli` take values in and return values out: they receive the current time, the terminal width and the file contents as arguments and are unit-tested without a filesystem or a real clock. `store`, `shell`, `prompt` and `clock` hold every effect: reading and writing files, moving directories, environment variables, the TTY and the time. A command handler reads through `store`, decides with pure functions, then writes through `store` in one place, after every check has passed.

### D5. Layout: hub, the `work` knowledge base, files named by ID

`WCM_HOME` (default `~/.wcm`) is the hub. This change only uses `<hub>/kbs/work/`, which it creates on first write; `config.yaml` and other knowledge bases arrive with `add-knowledge-bases`. An initiative is `kbs/work/initiatives/INIT-0007/INIT-0007.md` with `checkpoints/` beside it; closing moves the directory to `kbs/work/done/INIT-0007/`. There is no slug: Obsidian resolves `[[INIT-0007]]` only if the file is named that way (ADR 0002, decision 11). Discovery globs `initiatives/INIT-*/INIT-*.md` and `done/INIT-*/INIT-*.md`; anything else in the KB, `.obsidian/` included, is never read or written.

The same code on every OS: paths are built with `pathlib`, so `C:\Users\<user>\.wcm\kbs\work\...` on Windows and `/home/<user>/.wcm/kbs/work/...` on macOS and Linux.

### D6. Initiative file round-trip preserves what the tool does not own

`store.load` splits the file into four parts: frontmatter mapping, title heading, NOW block and `tail` (everything after the NOW block). `store.save` regenerates the first three from the model and appends `tail` verbatim. The frontmatter mapping is kept as a dict; known keys are updated in place, unknown keys pass through.

The title heading is the first `# ` line before `## NOW` and is always rendered from `title`, first in the body; when the frontmatter has no `title`, that heading provides it. Titles, like NOW values, are single lines. Whatever else precedes `## NOW` is kept, after the title. A body with no `## NOW` keeps what precedes its first other heading before the generated NOW block and the rest after it, so a second rewrite changes nothing. The NOW block starts at `## NOW` and ends at the next Markdown heading or end of file. Inside it, fields are matched by `**<Label>:**` at line start for the five labels, in any order; each value is the rest of that line. Any other non-blank line inside the block is not a field: it is kept verbatim after the five labels, which are rendered back in canonical order, with one blank line wherever the person left blank lines between them, and it counts toward the oversized-NOW warning. Nothing a person writes there is dropped. Rendering adds any known frontmatter key a hand-written file lacks, with its default (`null`, `[]`, `other`, `normal`).

`workspaces` is a list of mappings with `path` and `primary`; `--path` writes one primary entry with the directory made absolute. Unknown keys in an entry pass through, so F2 can add `repo`, `root` and `branch` without breaking the format.

*Alternative discarded:* a full Markdown AST library; the block has five known labels.

### D7. Atomic writes via temp file and `os.replace`

Every write of an initiative file goes to `<file>.tmp` in the same directory followed by `os.replace`. `done` checks first that `done/<ID>` does not exist, then moves the whole directory with one `os.rename`, and only then writes the final checkpoint and the status in `done/`. A refused or failed move leaves everything as it was. A plain rename, never `shutil.move`: on Windows a directory another program is using cannot be renamed, and `shutil.move` would fall back to copy-then-delete and leave half of it in each place.

### D8. IDs are scanned, not stored

`store.next_initiative_id()` scans directory names under `initiatives/` and `done/` matching `INIT-<digits>` and returns max + 1. `ids.parse` accepts `INIT-0007`, `init-7` and `7`, case-insensitively, and returns the canonical `INIT-0007`. A file whose name differs from its `id` is malformed (warned by `now`, refused by targeting commands).

### D9. Switch is one code path

`cli.py` has one pause flow in two halves: `_pause_fields` decides the new NOW values (flags, prompts or the previous values) and writes nothing; `_apply_pause` writes the checkpoint and the file and prints `Checkpoint saved.` / `Safe to switch context.`. `pause` uses it with trigger `pause`; `resume` and `new` validate the single-active invariant on disk, run `_pause_fields` on the current active initiative before writing anything, then `_apply_pause` with trigger `switch`, then activate or create the target. `done` writes a checkpoint with trigger `done` without prompts. Field flags reaching the pause flow always belong to the initiative being paused: `new` passes `--pause-next` there and keeps `--next` for the initiative it creates. When the next action is missing and there is no prompt, the error names the flag of the running command (`-n` for `pause`, `--pause-next` for `new`, `wcm pause -n` first for `resume`).

`resume` with no ID, or with the active ID, takes a separate read-only path: it renders the brief and asks `shell.py` for the directory change, without touching any file.

### D10. CD protocol through a file named by `WCM_CD_FILE`, not a stdout directive

The plan once sketched a `@@cd <path>` line on stdout. That requires the wrapper to capture stdout, which would buffer the interactive pause prompts until the process exits. Instead the wrapper creates an empty temp file, exports its path in `WCM_CD_FILE`, runs the CLI with all three streams attached to the console, and reads the file afterwards. The CLI writes the primary workspace path, UTF-8 without BOM, only when an initiative with an existing path is left active by `new` or `resume`.

*Alternative discarded:* prompts on stderr and streaming stdout; PowerShell 5.1 does not stream a native command's stdout until a newline, and prompts end without one.

### D11. Wrapper resolves the CLI once, forwards the exit code

```powershell
function wcm {
    $tmp = [System.IO.Path]::GetTempFileName()
    $env:WCM_CD_FILE = $tmp
    try {
        if ($script:WcmExe) { & $script:WcmExe @args } else { & py -3.14 -m wcm @args }
        $code = $LASTEXITCODE
        $target = (Get-Content -LiteralPath $tmp -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($target -and (Test-Path -LiteralPath $target -PathType Container)) { Set-Location -LiteralPath $target }
    } finally {
        Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
        Remove-Item Env:WCM_CD_FILE -ErrorAction SilentlyContinue
    }
    $global:LASTEXITCODE = $code
}
```

The sketch above is the shape; `shell/wcm.psm1` adds four details found in review:

- `wcm` is resolved with `Get-Command wcm -CommandType Application`; the function shadows the application by PowerShell's precedence rules, which is the intended effect. A found CLI is cached; a missing one is looked up again on every call, so installing it works without re-importing the module. A CLI that vanished after import (`CommandNotFoundException`) prints the install hint.
- Arguments are rebuilt before the call: PowerShell parses `--tags a,b` as an array, and relaying it through `@args` would split it into two arguments, so arrays are joined back with commas. In legacy native-argument mode (Windows PowerShell 5.1), empty arguments and arguments with spaces or double quotes are quoted Windows-style, because 5.1 drops the former and does not escape the latter.
- `-Encoding UTF8` matters: PowerShell 5.1 reads a file without BOM as ANSI.
- If neither the console script nor `py -3.14` with the package can start, the function prints an error that names `py -3.14 -m pip install` and sets `$LASTEXITCODE` to 1.

### D12. Time, ages and the stale-active warning

`clock.now()` returns `datetime.now().astimezone()` (local time with offset). Tests inject a fixed clock. Ages are humanised in `render.py` with the buckets `<60m -> Nm`, `<24h -> Nh Mm`, `<14d -> Nd`, else `Nw`. Checkpoint file names use the same clock formatted as `%Y-%m-%dT%H%M%S`.

The stale-active warning compares `now` with the most recent of `last_resumed` and the timestamp in the name of the newest checkpoint; above 4 hours it warns and suggests `wcm pause`. Counting from `last_resumed` keeps the warning quiet right after resuming something paused for days. 4 hours is a constant in `render.py` until `config.yaml` exists; `wcm checkpoint` (another remedy) arrives with `add-initiative-tools`.

### D13. Interactive detection and prompt semantics

`prompt.py` treats the flow as interactive only when `sys.stdin.isatty()` and no field flag was passed. It prints the ID and title of the initiative being paused, then prompts with `input()`, showing the previous value in brackets; Enter keeps, text replaces, a lone `-` clears. Tests drive the flow by monkeypatching `input` and `isatty`. A lone `-` at the `Next action` prompt is refused right away; an empty `Next` is refused after the prompts. Both happen before any file is touched.

### D14. File encoding

Every file of the store is written as UTF-8 without BOM, with `\n` line endings on every OS, so the same store reads the same on Windows, in Obsidian and in Git.

Console output differs by OS. On Windows, Python encodes redirected output in the ANSI code page, while PowerShell decodes it with the console's code page; when stdout is not a terminal, the CLI re-encodes it with `GetConsoleOutputCP()`, so accents survive `wcm now | Select-String`. On macOS and Linux nothing changes. Errors are replaced, never raised, and when the output encoding cannot represent `…` the truncation uses `...`. Truncation counts terminal columns, not characters: wide East Asian characters and most emoji take two.

## Risks / Trade-offs

- [Pause feels like a form and gets skipped] → prefilled prompts, Enter keeps, `-n` bypass; measured by hand during the Phase 1 exit test. If it still fails, the fix is product, not code.
- [The active initiative goes stale because work changed without telling WCM] → the 4-hour warning in `now`; the exit test records how often it fires.
- [`pip install` blocked on the corporate machine] → vendor PyYAML under `src/wcm/_vendor/`; no other dependency exists to block.
- [Python start-up makes `wcm now` feel slow] → keep imports minimal, measure with `Measure-Command { wcm now }` against a 20-initiative store; if above ~300 ms, lazy-import PyYAML and reconsider a .NET port as the plan suggests.
- [`python` on `PATH` is the Store alias] → wrapper prefers the installed `wcm` console script and falls back to `py -3.14 -m wcm`, never bare `python`.
- [Hand edits create inconsistent state] → warn in `now`, refuse in targeting commands, never auto-repair.
- [Two checkpoints in the same second] → numeric suffix on the file name.
- [A waiting initiative exists only by hand edit in this change] → `now` names it in a warning line instead of hiding it; `add-initiative-tools` adds the section.

## Migration Plan

Greenfield; nothing to migrate.

Install: clone, `py -3.14 -m pip install -e .`, add `Import-Module <repo>\shell\wcm.psm1` to `$PROFILE`, open a new shell, run `wcm now`.

Rollback: remove the profile line and `pip uninstall wcm`. `~/.wcm` is plain Markdown and can be kept, read, or deleted independently of the tool.
