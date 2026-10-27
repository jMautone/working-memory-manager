# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
SemVer with one minor per phase of the plan, and every merged change ships as
a pre-release of it; see [CONTRIBUTING.md](CONTRIBUTING.md).

## [Unreleased]

### Added

- [`persistent-working-memory-plan.md`](persistent-working-memory-plan.md) —
  the product plan: problem, principles, model, storage, the three core
  operations and the phases F1–F4 with their exit tests.
- OpenSpec project context and per-artifact rules.
- Release pipeline: every merged change publishes a GitHub pre-release with
  the sdist and the wheel of `wcm`, plus `checksums.txt`.
- `wcm`, the core of Phase 1: `new`, `now`, `pause`, `resume` and `done`.
  `pause` asks for the next action with the previous value prefilled and
  writes an append-only checkpoint; `resume` switches in one command and
  prints where you stopped; `now` shows the working set from any directory
  and warns about an active initiative left more than 4 hours without a
  checkpoint.
- Plain-text store in `~/.wcm/kbs/work` (`WCM_HOME` overrides the hub): one
  Markdown file per initiative, named by its ID, editable by hand and
  openable as an Obsidian vault.
- `shell/wcm.psm1`: a PowerShell module whose `wcm` function lets `resume`
  and `new` change the shell's directory through `WCM_CD_FILE`.
- `wcm note`: save a note in seconds, with the text as its title, linked to
  the active initiative (`--free` to skip the link), with tags (`-t`); with
  no text it asks for one line. `-e` opens it in the editor afterwards.
- `wcm note edit <ID>`: open a note in `VISUAL`, `EDITOR` or the OS default
  (`notepad` on Windows, `vi` elsewhere); after an edit only `updated`
  changes.
- `wcm notes`: find notes by text, tag (`-t`) or initiative (`-i`), newest
  first, one line each.
- Notes as plain Markdown files in `kbs/work/notes/NOTE-0012.md`, linked to
  their initiative with `initiative: "[[INIT-0007]]"`; notes written by hand
  in Obsidian are read too.
- The `wcm resume` brief shows `Notes:` with how many notes link to the
  initiative and the latest one.
