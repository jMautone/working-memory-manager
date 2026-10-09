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
