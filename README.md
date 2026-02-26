# SCALPEL

**Strategic Calendar Action Layer for Planning, Execution, and Logistics**

Mission-grade personal planning with Taskwarrior + calendar.

SCALPEL is a CLI-first planning and rendering toolchain for Taskwarrior users. It exports tasks, normalizes them into a versioned calendar payload, validates the payload/contracts, and renders a self-contained interactive HTML schedule for planning and execution.

## Status

Stable `1.0.0` release line. Core payload/schema/rendering interfaces are versioned and contract-tested. AI/planner helpers and optional integrations (for example LM Studio and nautical hooks) are available on top of that stable payload pipeline.

## Current Capabilities

- Turn your Taskwarrior tasks into a multi-day, interactive HTML calendar for planning and execution
- Work from a live Taskwarrior export or from saved payload JSON files when you want offline/repeatable runs
- Incorporated multiple themes and themes designed
- Apply plan overrides or AI-generated (local model) plan results before rendering to test scheduling changes safely
- Apply different colours for different project / tags/ goals
- Use optional nautical anchor/CP preview hooks if your Taskwarrior setup includes those fields
- Task actions: Add, Complete, Delete
- Notes
- Arrange functions for tasks
- 

SCALPEL is designed to grow into a broader personal planning system. Future development is intended to support military-inspired planning concepts such as Commander’s Intent, End State, PACE planning and alternative timelines, while remaining practical for individual use.

## Installation

Clone, install, and run locally:

```bash
git clone https://github.com/catanadj/taskwarrior-SCALPEL
cd taskwarrior-SCALPEL
python3 -m pip install .
scalpel --help
```

You can also install from an existing local checkout:

Local install:

```bash
python3 -m pip install .
```


If installing from PyPI, use the distribution name:

```bash
python3 -m pip install taskwarrior-scalpel
```

Primary CLI entrypoint after install/run:

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
