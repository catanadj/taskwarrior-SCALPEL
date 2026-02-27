<img width="1220" height="252" alt="SCALPEL banner" src="https://github.com/user-attachments/assets/0c87aec3-ca3c-4a4e-9b94-dce3c9c88689" />

![SCALPEL planning UI screenshot](https://github.com/user-attachments/assets/516dc7fb-ff6e-4754-a996-7805533763db)

# SCALPEL

## Mission-grade personal planning with Taskwarrior + calendar.

### **"When you plan that your plans may be interrupted or disturbed, you gain steadiness."**

Using standard calendar tools (Google Calendar and the like) you just set your schedule and then try your best to follow it but in real world as they say "no plan survives contact with the enemy" and surely the act of planning for alternative timelines/contingencies helps but how exactly can this be put in practice and with what tools?

I am sure that the commanders in the military have such tools but I could not find anything similar for individual/civilian use, especially not open source and local.

This project is my answer to that gap. 

In the current stage of development is not much different than a standard calendar application but in its advance form is going to be much more capable. 

Please support its development.

You can do so [here](https://paypal.me/catanadj) or [here](https://github.com/sponsors/catanadj) . Thank you.


## Status

Stable `1.0.0` release line.

- Core payload/schema/rendering interfaces are versioned and contract-tested.
- Replay/validation/filtering is part of the supported workflow.
- Planner/AI helpers (stub + optional LM Studio integration) are layered on top of the stable payload pipeline.

- A visual planning surface without giving up CLI workflows
- A reproducible pipeline (payload JSON + replay rendering)
- A safe way to test schedule changes before applying them in Taskwarrior
- Optional AI-assisted planning on top of a stable payload/render contract

Important: SCALPEL generates command output and plan JSON. It does not execute Taskwarrior commands automatically.

## Use

1. Run `scalpel` to export your Taskwarrior tasks and open a planning page in your browser.
2. Drag/resize tasks, queue adds/completes/deletes, and shape the schedule visually.
3. Copy the generated `task ... modify` / action commands or export a plan JSON for later replay/apply.

## Product Highlights

### Interactive planning UI

- Multi-day calendar with configurable work hours and vertical scale
- Drag/resize scheduling with snap-to-grid behavior
- Selection-driven planning actions
- Queue actions for selected tasks: complete, delete, add placeholders
- Copy command output for shell execution
- Export/import plan JSON (`scalpel.plan.v1`)
- Notes panel and quick command palette (`Ctrl/Cmd+K`)
- Goal/project/tag color mapping and theme customization
- Optional AI scheduling modal (works with the plan-result flow)

### CLI-first, replayable workflow

- Live Taskwarrior export -> payload -> HTML (`scalpel`)
- HTML -> extract embedded payload JSON (`scalpel-validate-payload --from-html`)
- Filter payloads with query syntax (`scalpel-filter-payload`)
- Re-render from payload JSON (`scalpel-render-payload`)
- Validate and upgrade payloads across schema versions (never downgrades)

### Planning + AI tooling

- Deterministic planner ops (`align-starts`, `align-ends`, `stack`, `distribute`, `nudge`) via `scalpel-plan-ops`
- Stub AI planner for deterministic local testing (`scalpel-ai-plan-stub`)
- Optional LM Studio local model integration (`scalpel-ai-plan-lmstudio`)
- Plan validation/apply tools (`scalpel-validate-plan-result`, `scalpel-apply-plan-result`)

## Installation

Requirements:

- Python `>=3.11`
- Taskwarrior installed on `PATH` for the main live-export command (`scalpel`)

Taskwarrior setup (`~/.taskrc`):

SCALPEL expects a `duration` UDA so generated commands like `duration:10min` round-trip cleanly.

```ini
uda.duration.type=duration
uda.duration.label=duration
uda.duration.default=PT10M
```

Install from PyPI:

```bash
python3 -m pip install taskwarrior-scalpel
```

Or from a local checkout:

```bash
python3 -m pip install .
```

Names:

- PyPI package: `taskwarrior-scalpel`
- Python module: `scalpel`
- Main CLI: `scalpel`

## Quick Start

Generate an interactive planning page from your live Taskwarrior data:

```bash
scalpel --out build/scalpel_schedule.html
```

Common options:

- `--filter "status:pending +work"`: Taskwarrior filter passed to `task export`
- `--start YYYY-MM-DD`: start date of the view
- `--days N`: number of days to show
- `--workhours HH:MM-HH:MM`: visible planning window
- `--tz` / `--display-tz`: bucketing vs display timezone
- `--plan-overrides FILE.json` / `--plan-result FILE.json`: apply changes before render

## Common Workflows

### 1) Daily planning from live Taskwarrior

```bash
scalpel --filter "status:pending" --days 7 --out build/scalpel.html
```

Then:

- Adjust the schedule in the browser
- Copy generated commands
- Review them
- Run them manually in your shell

### 2) Reproducible payload + replay workflow

Useful for debugging, sharing, testing, and offline iteration.

```bash
scalpel --no-open --out build/scalpel.html
scalpel-validate-payload --from-html build/scalpel.html --write-json build/payload.json
scalpel-filter-payload --in build/payload.json --q "project:work -blocked" --out build/work.json --pretty
scalpel-render-payload --in build/work.json --out build/work.html
```

### 3) AI-assisted planning (local-first)

Deterministic stub planner flow:

```bash
scalpel --no-open --out build/scalpel.html
scalpel-validate-payload --from-html build/scalpel.html --write-json build/payload.json

# build/selected.json contains a JSON array of selected task UUIDs
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

<details>
<summary><strong>Advanced: Query Language (Payload Filtering)</strong></summary>

<br />

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

</details>

<details>
<summary><strong>Advanced: Tooling Commands (Installed)</strong></summary>

<br />

Core workflow:

- `scalpel`
- `scalpel-render-payload`
- `scalpel-validate-payload`
- `scalpel-filter-payload`
- `scalpel-plan-ops`
- `scalpel-apply-plan-result`
- `scalpel-validate-plan-result`
- `scalpel-ai-plan-stub`
- `scalpel-ai-plan-lmstudio`

Engineering/support:

- `scalpel-doctor`
- `scalpel-check`
- `scalpel-ci`
- `scalpel-smoke-build`
- `scalpel-gen-fixtures`
- `scalpel-minify-fixture`
- `scalpel-ddmin-shrink`
- `scalpel-bench`

</details>

<details>
<summary><strong>Advanced: Public Python API (Stable Surface)</strong></summary>

<br />

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

</details>

<details>
<summary><strong>Advanced: Timezones</strong></summary>

<br />

SCALPEL separates two timezone concerns:

- Bucketing timezone (`--tz` / `SCALPEL_TZ`): controls day boundaries, `day_key`, and view-window anchoring.
- Display timezone (`--display-tz` / `SCALPEL_DISPLAY_TZ`): controls timestamp formatting in the HTML UI and generated command text.

Typical usage:

- Interactive local use: `--tz local --display-tz local` (defaults)
- Deterministic CI/fixtures: `--tz UTC` and choose display (`local` or `UTC`)

</details>

<details>
<summary><strong>Advanced: Nautical Hooks (Optional)</strong></summary>

<br />

Nautical preview task expansion is enabled by default.

- Disable per run: `scalpel --no-nautical-hooks`
- Control default via env: `SCALPEL_ENABLE_NAUTICAL_HOOKS=0|1`

When enabled, SCALPEL attempts to load `nautical_core` (including from `~/.task` / `~/.task/hooks` if present) and generate anchor/CP preview tasks.

</details>

<details>
<summary><strong>Advanced: Docs / References</strong></summary>

<br />

- `docs/AI_FLOW.md`
- `docs/AI_INTERFACE.md`
- `docs/PLANNER_CORE.md`
- `docs/SCHEMA_EVOLUTION_PROTOCOL.md`
- `docs/PACKAGING_RELEASE_CHECKLIST.md`

Golden fixture maintenance:

```bash
scalpel-gen-fixtures --check
scalpel-gen-fixtures --write
```

</details>
