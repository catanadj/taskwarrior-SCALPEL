# Planner Core (Contract)

Goal: keep scheduling behavior deterministic and testable outside the UI.

## Inputs

- `tasks`: list of payload tasks (dicts).
- `overrides`: dict of `{uuid: PlanOverride}`.
- `cfg`: payload cfg (work hours, timezone, defaults).

## Outputs

- `apply_overrides(...)` returns `{uuid: (start_ms, due_ms, duration_min)}`.
- `detect_conflicts(...)` returns overlap segments and out-of-hours segments.
- `selection_metrics(...)` returns duration/span/gap totals for a set of uuids.

## Fixture Contract

See `tests/fixtures/planner_core_fixture.json` and
`tests/test_contract_planner_core_fixture.py` for the locked behavior.
