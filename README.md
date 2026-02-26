<img width="1220" height="252" alt="image" src="https://github.com/user-attachments/assets/0c87aec3-ca3c-4a4e-9b94-dce3c9c88689" />

![Screenshot](https://github.com/user-attachments/assets/516dc7fb-ff6e-4754-a996-7805533763db)


# Mission-grade personal planning with Taskwarrior + calendar.

SCALPEL is a CLI-first planning and rendering toolchain for Taskwarrior users. It exports tasks, normalizes them into a versioned calendar payload, validates the payload/contracts, and renders a self-contained interactive HTML planning view.

## Status

Stable `1.0.0` release line.

- Core payload/schema/rendering interfaces are versioned and contract-tested.
- Replay/validation/filtering tooling is part of the supported workflow.
- Planner/AI helpers (stub + optional LM Studio integration) sit on top of the stable payload pipeline.

SCALPEL is designed to grow into a broader personal planning system. Future development is intended to support military-inspired planning concepts such as Commander’s Intent, End State, PACE planning and alternative timelines, while remaining practical for individual use.

## What SCALPEL Actually Ships

SCALPEL is more than a single HTML renderer. It includes:

- A primary CLI (`scalpel`) that runs a live `task export` and produces an interactive schedule HTML.
- A versioned payload pipeline (schema validation, upgrades, extraction from HTML, replay rendering).
- A query/filter toolchain for payload JSON using `scalpel` query syntax.
- Planner operations (`align-starts`, `align-ends`, `stack`, `distribute`, `nudge`) via CLI tools and AI plan formats.
- Optional local AI planning via LM Studio (OpenAI-compatible API).
- Diagnostics, smoke-build, fixture, benchmark, delta-debugging, and CI helper commands.
- A small public Python API for loading/normalizing/querying payloads.

## Core Capabilities

### Main workflow (`scalpel`)

- Export from Taskwarrior (`task ... export`) using a filter (default `status:pending`)
- Normalize tasks into a SCALPEL payload with indices (`by_uuid`, `by_status`, `by_project`, `by_tag`, `by_day`)
- Render a self-contained interactive HTML calendar (no server required)
- Open the rendered page automatically (optional `--no-open`)

### Interactive HTML planning UI

The generated page supports a planning-first workflow and exports commands/results for you to apply:

- Drag/resize calendar tasks with snap-to-grid behavior
- Multi-day calendar view with configurable work hours and vertical scale
- Selection-driven planning actions and command generation
- Queue `task` actions for selected tasks (`complete`, `delete`) and local placeholder task adds
- Copy/export generated Taskwarrior command output (SCALPEL does not run commands automatically)
- Export/import plan JSON (`scalpel.plan.v1` plan result format)
- Notes panel and quick command palette (`Ctrl/Cmd+K`)
- Goal/tag/project color mapping and theme customization
- Optional AI scheduling modal in the UI (paired with the plan-result workflow)

### Replayable, inspectable pipeline

- Render from live Taskwarrior data (`scalpel`)
- Render from saved payload JSON (`scalpel-render-payload`)
- Extract embedded payload JSON from generated HTML (`scalpel-validate-payload --from-html`)
- Validate and upgrade payloads across schema versions (never downgrades)
- Filter payloads with query syntax and re-render subsets

### Planner + AI workflows

- Apply deterministic planner ops to selected UUIDs (`scalpel-plan-ops`)
- Validate AI plan result files (`scalpel-validate-plan-result`)
- Apply AI plan results to payloads (`scalpel-apply-plan-result`)
- Generate deterministic stub plans for local testing (`scalpel-ai-plan-stub`)
- Call LM Studio as a local planner backend (`scalpel-ai-plan-lmstudio`)

### Engineering/tooling support

- Repo hygiene and preflight checks (`scalpel-doctor`, `scalpel-check`)
- One-command CI gate (`scalpel-ci`)
- Smoke HTML/payload generation (`scalpel-smoke-build`)
- Golden fixture generation/checking (`scalpel-gen-fixtures`)
- Micro-benchmarks (`scalpel-bench`)
- Delta-debug shrinking for failing payloads (`scalpel-ddmin-shrink`)

## Installation

Requirements:

- Python `>=3.11`
- Taskwarrior installed on `PATH` for the main live-export command (`scalpel`)

Install from PyPI (distribution name):

```bash
python3 -m pip install taskwarrior-scalpel
```

Or install from a local checkout:

```bash
python3 -m pip install .
```

Primary CLI entrypoint after install:

```bash
scalpel --help
```

Additional tool commands are also installed (for example `scalpel-render-payload`, `scalpel-filter-payload`, `scalpel-plan-ops`, `scalpel-ci`).

Notes:

- PyPI distribution name: `taskwarrior-scalpel`
- Python package/module namespace: `scalpel`
- Main CLI: `scalpel`

## Quick Start

Generate an interactive planning page from Taskwarrior:

```bash
scalpel --no-open --out build/scalpel_schedule.html
```

Useful options:

- `--filter "status:pending +work"`: Taskwarrior filter passed to `task export`
- `--start YYYY-MM-DD`: view start date
- `--days N`: number of days to render
- `--workhours HH:MM-HH:MM`: visible planning window
- `--tz` / `--display-tz`: bucketing vs display timezone
- `--plan-overrides FILE.json` or `--plan-result FILE.json`: apply changes before render

## Reproducible / Offline Workflow (Payload Replay)

Generate HTML, extract payload, validate, filter, and re-render:

```bash
scalpel --no-open --out build/scalpel.html
scalpel-validate-payload --from-html build/scalpel.html --write-json build/payload.json
scalpel-filter-payload --in build/payload.json --q "project:work -blocked" --out build/work.json --pretty
scalpel-render-payload --in build/work.json --out build/work.html
```

This workflow is useful for debugging, reproducibility, testing, and sharing minimal fixtures.

## Query Language (Payload Filtering)

`scalpel-filter-payload` uses the SCALPEL query language (`scalpel.query_lang`).

Supported filters include:

- `uuid:<id>`
- `project:<name>[,<name>...]`
- `status:<status>[,<status>...]`
- `day:YYYY-MM-DD`
- `+tag` / `tag:tag1,tag2`
- `-tag` (exclude tag)
- `desc:substring`
- `desc~regex` / `desc!~regex`
- Bare tokens (description substring match, case-insensitive)

Examples:

```bash
scalpel-filter-payload --in build/payload.json --q "project:work +focus -blocked" --out build/focus.json
scalpel-filter-payload --in build/payload.json --q "day:2026-02-26 desc~meeting" --out build/meetings.json
```

## Planner / AI Flow (CLI)

Deterministic local flow (stub planner):

```bash
scalpel --no-open --out build/scalpel.html
scalpel-validate-payload --from-html build/scalpel.html --write-json build/payload.json

# build/selected.json should contain a JSON array of task UUIDs
scalpel-ai-plan-stub --in build/payload.json --selected build/selected.json --prompt "align starts" --out build/plan.json --plan-schema v2
scalpel-apply-plan-result --in build/payload.json --plan build/plan.json --out build/payload_planned.json
scalpel-render-payload --in build/payload_planned.json --out build/scalpel_planned.html
```

Optional LM Studio backend:

```bash
scalpel-ai-plan-lmstudio \
  --in build/payload.json \
  --selected build/selected.json \
  --prompt "align starts" \
  --out build/plan.json \
  --base-url http://127.0.0.1:1234 \
  --model your-model-name
```

See `docs/AI_FLOW.md`, `docs/AI_INTERFACE.md`, and `docs/PLANNER_CORE.md` for contracts and formats.

## Tooling Commands (Installed)

Main user-facing commands:

- `scalpel` - live Taskwarrior export -> normalized payload -> rendered HTML
- `scalpel-render-payload` - render payload JSON to replay HTML
- `scalpel-validate-payload` - validate payload JSON or extract+validate from HTML
- `scalpel-filter-payload` - query/filter payload JSON
- `scalpel-plan-ops` - apply deterministic planner ops to selected tasks
- `scalpel-apply-plan-result` - apply AI plan result JSON to a payload
- `scalpel-validate-plan-result` - validate AI plan JSON format
- `scalpel-ai-plan-stub` - deterministic stub AI planner (good for testing)
- `scalpel-ai-plan-lmstudio` - LM Studio local model planner integration

Engineering/support commands:

- `scalpel-doctor`
- `scalpel-check`
- `scalpel-ci`
- `scalpel-smoke-build`
- `scalpel-gen-fixtures`
- `scalpel-minify-fixture`
- `scalpel-ddmin-shrink`
- `scalpel-bench`

## Public Python API (Stable Surface)

Import from `scalpel.api` (preferred) or `import scalpel` (re-export).

Contract-tested public API includes:

- `load_payload_from_json(...)`
- `load_payload_from_html(...)`
- `normalize_payload(...)`
- `iter_tasks(...)`
- `task_by_uuid(...)`
- `tasks_by_status(...)`
- `tasks_by_project(...)`
- `tasks_by_tag(...)`
- `tasks_by_day(...)`
- `filter_payload(...)`

Example:

```python
from scalpel.api import load_payload_from_html, tasks_by_day

payload = load_payload_from_html("build/scalpel.html")
today = tasks_by_day(payload, "2026-02-26")
print(len(today))
```

## Timezones

SCALPEL separates two timezone concerns:

- Bucketing timezone (`--tz` / `SCALPEL_TZ`): controls day boundaries, `day_key`, and view-window anchoring.
- Display timezone (`--display-tz` / `SCALPEL_DISPLAY_TZ`): controls timestamp formatting in the HTML UI and generated command text.

Typical usage:

- Interactive local use: `--tz local --display-tz local` (defaults)
- Deterministic CI/fixtures: `--tz UTC` and choose display (`local` or `UTC`)

## Nautical Hooks (Optional)

Nautical preview task expansion is enabled by default.

- Disable per run: `scalpel --no-nautical-hooks`
- Control default via env: `SCALPEL_ENABLE_NAUTICAL_HOOKS=0|1`

When enabled, SCALPEL attempts to load `nautical_core` (including from `~/.task` / `~/.task/hooks` if present) and generate anchor/CP preview tasks.

## Packaging / Release / Docs

- Packaging metadata: `pyproject.toml`
- Release checklist: `docs/PACKAGING_RELEASE_CHECKLIST.md`
- Schema evolution notes: `docs/SCHEMA_EVOLUTION_PROTOCOL.md`
- AI contracts/flows: `docs/AI_INTERFACE.md`, `docs/AI_FLOW.md`, `docs/PLANNER_CORE.md`

Golden fixture maintenance:

```bash
scalpel-gen-fixtures --check
scalpel-gen-fixtures --write
```
