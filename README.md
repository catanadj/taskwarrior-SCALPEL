# SCALPEL

Taskwarrior planning UI with a calendar-first workflow.

SCALPEL exports Taskwarrior tasks into a local browser planner. You can drag, resize, add draft tasks, queue actions, review generated `task ...` commands, then either copy them or apply them through the live local server after confirmation.

![SCALPEL planning UI screenshot](https://github.com/user-attachments/assets/516dc7fb-ff6e-4754-a996-7805533763db)

## Status

Stable `1.0.0` release line.

- Payload, schema, rendering, replay, and validation paths are contract-tested.
- Live mode is the normal day-to-day workflow.
- `--once` remains available for render-only / copy-only use.
- AI/planner helpers are optional layers on top of the stable payload pipeline.

## Requirements

- Python `>=3.11`
- Taskwarrior on `PATH` for live export and live apply

Recommended Taskwarrior UDA:

```ini
uda.duration.type=duration
uda.duration.label=duration
uda.duration.default=PT10M
```

## Install

From PyPI:

```bash
python3 -m pip install taskwarrior-scalpel
```

From a local checkout:

```bash
python3 -m pip install .
```

Developer setup:

```bash
./scripts/scalpel_dev.sh setup
```

Names:

- PyPI package: `taskwarrior-scalpel`
- Python module: `scalpel`
- Main CLI: `scalpel`

## Quick start

```bash
scalpel --filter "status:pending" --days 7 --out build/scalpel.html
```

Then use the browser UI to:

- drag or resize scheduled tasks
- queue add / complete / delete actions
- review planning warnings for overlaps, out-of-hours tasks, and overbooked days
- copy generated commands or apply them directly in live mode
- refresh from Taskwarrior without restarting the process

Common options:

```bash
scalpel \
  --filter "status:pending +work" \
  --start 2026-07-19 \
  --days 7 \
  --workhours 09:00-17:00 \
  --out build/scalpel.html
```

Useful flags:

- `--once`: render HTML and exit; no live server
- `--no-open`: do not open the browser automatically
- `--show-completed`: include completed tasks in the payload
- `--no-nautical-hooks`: disable Nautical preview expansion
- `--tz` / `--display-tz`: control day bucketing and timestamp display
- `--plan-overrides FILE.json`: apply local plan overrides before rendering
- `--plan-result FILE.json`: apply planner/AI result before rendering

Remote/LAN live mode requires explicit auth:

```bash
scalpel --allow-remote --serve-token "$TOKEN" --host 0.0.0.0 --out build/scalpel.html
```

## Daily workflow

1. Start SCALPEL:

   ```bash
   scalpel --filter "status:pending" --days 7 --out build/scalpel.html
   ```

2. Plan in the browser:

   - drag / resize tasks
   - select tasks and use arrangement actions
   - use `Next free slot` or `Rebalance day`
   - add local placeholder tasks
   - use `Ctrl/Cmd+K` for search and commands
   - use `Ctrl/Cmd+Z` / `Ctrl/Cmd+Shift+Z` for undo / redo

3. Commit changes to Taskwarrior:

   - copy the generated commands and run them manually, or
   - use live apply, select commands, preview, and confirm

Live mode exposes local endpoints for refresh, task lookup, Timewarrior import, client-state persistence, health, and metrics. Non-loopback access requires `--allow-remote` plus a serve token.

## Replayable payload workflow

Use this for debugging, sharing, testing, and offline iteration.

```bash
scalpel --once --no-open --out build/scalpel.html
scalpel-validate-payload --from-html build/scalpel.html --write-json build/payload.json
scalpel-filter-payload --in build/payload.json --q "project:work -blocked" --out build/work.json --pretty
scalpel-render-payload --in build/work.json --out build/work.html
```

Query examples:

```bash
scalpel-filter-payload --in build/payload.json --q "project:work +focus -blocked" --out build/focus.json
scalpel-filter-payload --in build/payload.json --q "day:2026-07-19 desc~meeting" --out build/meetings.json
```

Supported query forms include `uuid:`, `project:`, `status:`, `day:YYYY-MM-DD`, `+tag`, `-tag`, `desc:substring`, `desc~regex`, and bare description tokens.

## Planner / AI workflow

Deterministic local stub:

```bash
scalpel --once --no-open --out build/scalpel.html
scalpel-validate-payload --from-html build/scalpel.html --write-json build/payload.json

# build/selected.json is a JSON array of selected task UUIDs.
scalpel-ai-plan-stub \
  --in build/payload.json \
  --selected build/selected.json \
  --prompt "align starts" \
  --out build/plan.json \
  --plan-schema v2

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

Deterministic planner operations are also available through `scalpel-plan-ops`.

## Installed commands

Core:

- `scalpel`
- `scalpel-render-payload`
- `scalpel-validate-payload`
- `scalpel-filter-payload`
- `scalpel-plan-ops`
- `scalpel-apply-plan-result`
- `scalpel-validate-plan-result`
- `scalpel-ai-plan-stub`
- `scalpel-ai-plan-lmstudio`

Engineering:

- `scalpel-doctor`
- `scalpel-check`
- `scalpel-ci`
- `scalpel-smoke-build`
- `scalpel-gen-fixtures`
- `scalpel-minify-fixture`
- `scalpel-ddmin-shrink`
- `scalpel-bench`

## Public Python API

Use `scalpel.api` for the stable public API.

```python
from scalpel.api import load_payload_from_html, tasks_by_day

payload = load_payload_from_html("build/scalpel.html")
today = tasks_by_day(payload, "2026-07-19")
print(len(today))
```

Contract-tested functions include payload loading, normalization, task iteration, task lookup by UUID/status/project/tag/day, and payload filtering.

## Timezones

SCALPEL separates:

- bucketing timezone: `--tz` / `SCALPEL_TZ`
- display timezone: `--display-tz` / `SCALPEL_DISPLAY_TZ`

Use local defaults for interactive planning. Use UTC for deterministic fixtures and CI.

## Nautical hooks

Nautical preview task expansion is enabled by default.

- Disable per run: `scalpel --no-nautical-hooks`
- Control default: `SCALPEL_ENABLE_NAUTICAL_HOOKS=0|1`

SCALPEL checks for `nautical_core` under `~/.task/nautical_core/` and `~/.task/hooks/nautical_core/`, then falls back to legacy artefacts and normal Python imports.

## Development checks

```bash
./scripts/scalpel_dev.sh test
scalpel-check
scalpel-gen-fixtures --check
```

Update golden fixtures:

```bash
scalpel-gen-fixtures --write
```

## Docs

- [AI flow](docs/AI_FLOW.md)
- [AI interface](docs/AI_INTERFACE.md)
- [Planner core](docs/PLANNER_CORE.md)
- [Schema evolution protocol](docs/SCHEMA_EVOLUTION_PROTOCOL.md)
- [Packaging release checklist](docs/PACKAGING_RELEASE_CHECKLIST.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Support

If SCALPEL is useful to you, you can support development through [GitHub Sponsors](https://github.com/sponsors/catanadj) or [PayPal](https://paypal.me/catanadj).
