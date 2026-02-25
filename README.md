# SCALPEL

**Strategic Calendar Action Layer for Planning, Execution, and Logistics**

Mission-grade personal planning with Taskwarrior + Calendar.


SCALPEL is a planning and rendering toolchain that turns Taskwarrior/Timewarrior data into a validated calendar payload and a single-file HTML planning view. It is built for people who want a precise, inspectable workflow for scheduling, execution, and daily control while staying in CLI-first tooling.

Today, SCALPEL focuses on:
- generating and normalizing Taskwarrior calendar payloads
- validating payloads and schema contracts for reliable automation
- rendering a self-contained HTML calendar view for review and execution
- supporting planner/AI-assisted workflows through contract-driven tooling

SCALPEL is designed to grow into a broader personal planning system. Future development is intended to support military-inspired planning concepts such as Commander’s Intent, End State, PACE planning and alternative timelines, while remaining practical for individual use.

## Status

Stable `1.0.0` release line. Interfaces and schemas are versioned, and future changes may introduce new versions as the project evolves.

## Installation

Local install:

```bash
python3 -m pip install .
```


If installing from PyPI, use the distribution name:

```bash
python3 -m pip install taskwarrior-scalpel
```

Primary CLI entrypoint after install:

```bash
scalpel --help
```

Tooling commands are also installed (for example `scalpel-smoke-build`, `scalpel-validate-payload`, `scalpel-ci`).

The PyPI distribution name is `taskwarrior-scalpel`; the Python module namespace and CLI remain `scalpel`.

## Packaging / Release

Packaging metadata is defined in `pyproject.toml`. A release checklist is available at `docs/PACKAGING_RELEASE_CHECKLIST.md`.

## Timezones

SCALPEL (`scalpel`) separates two concerns:

Bucketing timezone (`--tz` / `SCALPEL_TZ`) - Controls day boundaries (`day_key`), view-window midnight anchoring, and fixture determinism.

Display timezone (`--display-tz` / `SCALPEL_DISPLAY_TZ`) - Controls how timestamps are formatted in the HTML UI (panels, tooltips, commands). Day headers remain aligned to the bucketing timezone.

Typical usage:

Normal interactive use: `--tz local --display-tz local` (defaults).

Deterministic CI and golden fixtures: `--tz UTC` with either `--display-tz local` (human-friendly) or `--display-tz UTC` (screenshot-stable).

## Nautical Hooks

Nautical preview task expansion is enabled by default.

Disable it for a run:

```bash
python -m scalpel.cli --no-nautical-hooks
```

You can also control default behavior via env (`SCALPEL_ENABLE_NAUTICAL_HOOKS=0|1`).

When enabled, `scalpel` loads `nautical_core` (including from `~/.task` / `~/.task/hooks` if present) and generates anchor/CP preview tasks.


Check/update golden fixtures:

```bash
python -m scalpel.tools.gen_fixtures --check
python -m scalpel.tools.gen_fixtures --write
```
