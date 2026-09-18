## Context

See proposal.md for motivation. This is a greenfield repository: one commit holding `persistent-working-memory-plan.md` and an empty OpenSpec root. The plan's sections 4, 6, 7, 15 and 17 fix the shape of the product; this design fills in the technical choices needed to build Phase 1 and records where it deviates from the plan's sketches.

Environment facts that shape the approach (observed on the target machine):

- Python 3.14.4 is installed via the Windows launcher (`py -3.14`). The `python` on `PATH` is the Microsoft Store alias, not that interpreter.
- No YAML or frontmatter packages are installed. `pip` availability on this corporate machine is unverified.
- Shell is Windows PowerShell 5.1 (no `&&`, no ternary). The wrapper must run there.
- No Node dependency is acceptable for the tool itself.

The requirements themselves live in the six delta specs under `specs/`; this document does not restate them.

## Goals / Non-Goals

**Goals:**

- A `wcm now` that starts and renders in well under a second on a store of ~20 initiatives, because it is the most-run command.
- Every file the tool writes is something a person would write by hand: no generated indexes, no hidden state, no counters.
- Tests can exercise every command end to end against a temporary store, including the interactive pause flow and the Phase 1 exit sequence.
- The PowerShell wrapper is thin enough to be read in one screen and never needs to parse CLI output.

**Non-Goals:**

- Anything the proposal lists as out of scope (Git, sessions, agents, search, sync).
- Colour or rich terminal UI. Plain text first; colour can be layered later without touching behaviour.
- Cross-platform shell wrappers. Only PowerShell ships in Phase 1; the CD protocol is shell-agnostic so bash/zsh wrappers can be added later.
- Locking for concurrent writers. One person, one machine, sequential commands.

## Decisions

### D1. Python 3.14 with `argparse`, no CLI framework

`argparse` from the standard library builds the subcommand tree (`new`, `now`, `capture`, `inbox`, `promote`, `pause`, `resume`, `list`, `show`, `wait`, `done`, `checkpoint`, `edit`). Exit codes: `0` success, `1` domain error (unknown ID, invariant refused, malformed file), `2` usage error (argparse default).

*Alternatives:* `click`/`typer` give nicer help but add imports on every start of `wcm now` and a dependency to install. The command surface is small and stable enough that argparse's verbosity is a one-time cost.

### D2. PyYAML is the only runtime dependency

Frontmatter is loaded with `yaml.safe_load` and written with `yaml.safe_dump(sort_keys=False, allow_unicode=True)` so hand-added keys survive and key order stays readable. Timestamps are written as ISO 8601 strings, not YAML timestamps, so they round-trip unchanged.

*Alternatives:* a hand-rolled parser for the flat subset the tool writes was rejected because the files are explicitly hand-editable: a person will use flow lists, quotes, and nested maps the subset parser would choke on. If `pip install` proves blocked on the target machine, fall back to vendoring PyYAML under `src/wcm/_vendor/` rather than writing a parser (recorded as a risk below).

### D3. Package layout and entry points

```text
pyproject.toml            name "wcm", console script wcm = wcm.cli:main
src/wcm/__init__.py
src/wcm/__main__.py       python -m wcm → cli.main
src/wcm/cli.py            argparse tree, one handler per command, exit codes
src/wcm/store.py          root resolution (WCM_HOME), layout paths, ID derivation,
                          initiative discovery, atomic write, done/ move
src/wcm/model.py          Initiative dataclass, states, priorities, NOW block
                          parse/render, invariant checks
src/wcm/checkpoint.py     checkpoint file naming and rendering
src/wcm/inbox.py          capture line format, parse/append/remove, CAP ID derivation
src/wcm/prompt.py         pause prompt flow (TTY detection, prefill, dash-to-clear)
src/wcm/render.py         now/list/show/resume output, humanised ages, truncation
src/wcm/shell.py          WCM_CD_FILE protocol
src/wcm/clock.py          now() in local time with offset; injectable for tests
shell/wcm.psm1            PowerShell wrapper
tests/                    pytest; every test points WCM_HOME at tmp_path
README.md                 install, profile line, storage format, hand-editing rules
```

Installed with `py -3.14 -m pip install -e .` so a `wcm` console script lands on `PATH`. The wrapper prefers that script (D8).

### D4. Initiative file round-trip preserves what the tool does not own

`store.load` splits the file into three parts: frontmatter mapping, NOW block, and `tail` (everything after the NOW block). `store.save` regenerates the first two from the model and appends `tail` verbatim. The frontmatter mapping is kept as a dict; known keys are updated in place, unknown keys pass through. This is what makes "hand-editable" true rather than aspirational.

The NOW block is parsed by matching `**<Label>:**` at line start for the five labels, in any order, taking the rest of the line (and continuation lines until the next label) as the value. It is always rendered back in canonical order with all five labels present.

*Alternative:* a full Markdown AST library. Overkill: the block has five known labels.

### D5. Atomic writes via temp file and `os.replace`

Every write of `initiative.md` or `inbox.md` goes to `<file>.tmp` in the same directory followed by `os.replace`. Directory moves for `done` use `shutil.move` on the whole initiative directory after the final checkpoint and status write succeed inside `initiatives/`, so a failure mid-move leaves a consistent initiative in one of the two places.

### D6. IDs are scanned, not stored

`store.next_initiative_id()` globs `initiatives/INIT-*` and `done/INIT-*`, parses the four-digit number from each directory name, and returns max + 1. `inbox.next_capture_id()` scans `inbox.md` lines plus the `capture` frontmatter field of every initiative. Both are O(number of initiatives), which is instantaneous at the expected scale and removes the only piece of state that could drift.

### D7. Switch is one code path

`cli.py` has a single `_switch(target)` helper used by `resume`, `new`, and `promote --resume`: it validates the single-active invariant on disk, runs `_pause_flow(current_active, trigger="switch")` if applicable, then activates the target. `pause` calls `_pause_flow(target, trigger="pause")` and stops. `wait` calls `_pause_flow(target, trigger="wait")` and then sets `waiting_on`. `done` writes a checkpoint with trigger `done` without prompts. One flow, four triggers, no duplicated invariant logic.

### D8. CD protocol through a file named by `WCM_CD_FILE`, not a stdout directive

The plan sketches a `@@cd <path>` line on stdout that the wrapper consumes. That requires the wrapper to capture stdout, which would buffer the interactive pause prompts until the process exits and break the core `resume`-with-switch flow. Instead the wrapper creates an empty temp file, exports its path in `WCM_CD_FILE`, runs the CLI with all three streams attached to the console, and reads the file afterwards. The CLI writes the path only when an initiative with an existing `path` becomes active. The protocol is shell-agnostic and trivially testable.

*Alternative kept for later:* printing prompts on stderr and streaming stdout. Rejected because PowerShell 5.1 does not stream a native command's stdout to a `ForEach-Object` until a newline, and prompts end without one.

### D9. Wrapper resolves the CLI once, forwards the exit code

```powershell
function wcm {
    $tmp = [System.IO.Path]::GetTempFileName()
    $env:WCM_CD_FILE = $tmp
    try {
        if ($script:WcmExe) { & $script:WcmExe @args } else { & py -3.14 -m wcm @args }
        $code = $LASTEXITCODE
        $target = (Get-Content -LiteralPath $tmp -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($target -and (Test-Path -LiteralPath $target -PathType Container)) { Set-Location -LiteralPath $target }
    } finally {
        Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
        Remove-Item Env:WCM_CD_FILE -ErrorAction SilentlyContinue
    }
    $global:LASTEXITCODE = $code
}
```

`$script:WcmExe` is resolved at import with `Get-Command wcm -CommandType Application`. The function shadows the application by PowerShell's precedence rules, which is the intended effect.

### D10. Time and ages

`clock.now()` returns `datetime.now().astimezone()` (local time with offset). Tests inject a fixed clock. Ages are humanised in `render.py` with the buckets `<60m → Nm`, `<24h → Nh Mm`, `<14d → Nd`, else `Nw`. Checkpoint file names use the same clock formatted as `%Y-%m-%dT%H%M%S`.

### D11. Interactive detection and prompt semantics

`prompt.py` treats the flow as interactive only when `sys.stdin.isatty()` and no field flag was passed. Prompts use `input()` with the previous value shown in brackets; Enter keeps, text replaces, a lone `-` clears. Tests drive the flow by monkeypatching `input` and `isatty`. Refusal to pause when `Next` is empty is checked once, after the prompts, before any file is touched.

### D12. Editor resolution

`edit` and `checkpoint --edit` run `$VISUAL`, else `$EDITOR`, else `notepad`, via `subprocess.run(shlex.split(cmd) + [path])` and wait. The README tells VS Code users to set `EDITOR="code --wait"`.

## Risks / Trade-offs

- [Pause feels like a form and gets skipped] → prefilled prompts, Enter keeps, `-n` bypass; measured by hand during the Phase 1 exit test. If it still fails, the fix is product, not code.
- [`pip install` blocked on the corporate machine] → vendor PyYAML under `src/wcm/_vendor/` and import from there; no other dependency exists to block.
- [Python start-up makes `wcm now` feel slow] → keep imports minimal, measure with `Measure-Command { wcm now }` against a 20-initiative store; if above ~300 ms, lazy-import PyYAML and reconsider a .NET port as the plan suggests.
- [`python` on `PATH` is the Store alias] → wrapper prefers the installed `wcm` console script and falls back to `py -3.14 -m wcm`, never bare `python`.
- [Hand edits create inconsistent state] → warn in `now`/`list`, refuse in activating commands, never auto-repair. The person stays in control of their own files.
- [Two checkpoints in the same second] → numeric suffix on the file name.
- [Editor returns immediately (e.g. `code` without `--wait`)] → validation after edit runs against the unchanged file; documented, not worked around.
- [Slug derived from a title with only non-ASCII characters is empty] → fall back to `initiative` as the slug; the ID remains the identity.

## Migration Plan

Greenfield; nothing to migrate.

Install: clone, `py -3.14 -m pip install -e .`, add `Import-Module <repo>\shell\wcm.psm1` to `$PROFILE`, open a new shell, run `wcm now`.

Rollback: remove the profile line and `pip uninstall wcm`. `~/.wcm` is plain Markdown and can be kept, read, or deleted independently of the tool.
