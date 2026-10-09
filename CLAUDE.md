# working-memory-manager

`wcm` is a working memory layer: it lets a person interrupt any initiative and
resume it later in under 30 seconds, without rereading conversations. Python
3.14 CLI plus a PowerShell module; Windows is the daily machine.

## Read first

- `persistent-working-memory-plan.md`: the problem, principles, model, storage
  and the phases F1..F4 with their exit tests. It is the source of truth for
  what comes next (§14).
- `openspec/config.yaml`: product context, non-negotiable principles, stack,
  and the rules each OpenSpec artifact follows.
- `CONTRIBUTING.md`: branches, pull request titles, versions, releases, and
  [Working on an OpenSpec change](CONTRIBUTING.md#working-on-an-openspec-change).

## How work flows

Every change to what `wcm` does is an OpenSpec change, on its own branch:

```
vX.Y/<change> -> /opsx:propose -> author approves -> /opsx:apply
  -> CHANGELOG + PR -> /opsx:archive (same PR) -> squash merge
```

- Never commit to `main`. Pick the branch prefix from `CONTRIBUTING.md`.
- After `/opsx:propose`, stop and wait for the author to approve the
  artifacts. Do not start `/opsx:apply` on your own.
- Archive in the change's own pull request, before the merge, always syncing
  the specs.
- Before pushing a pull request, `git fetch origin` and check its title with
  `python tools/relcheck.py pr --branch "$(git branch --show-current)" --title "<title>"`.

## Checks

The CI runs these on Windows, macOS and Linux; run them on Windows before
closing a task:

```sh
py -3.14 -m ruff check .
py -3.14 -m ruff format --check .
py -3.14 -m pytest tools
py -3.14 -m pytest
openspec validate --all --strict
```

Tasks marked **[manual]** are verified by hand, not by CI alone.

## Language

Code, comments, CLI output, help, specs and `README`/`CONTRIBUTING`/`CHANGELOG`
in English. `proposal.md`, `design.md`, `tasks.md`, the plan,
`docs/decisions/` and pull request bodies in Spanish.
