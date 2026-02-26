# AI Scheduling Interface (Internal)

Goal: define a stable boundary between the core calendar payload and any AI-based
planner so the calendar/render pipeline stays resilient as AI evolves.

## Inputs

Use `scalpel.ai.AiPlanRequest`:

- `payload`: normalized scalpel payload (schema v1+), same structure used by render.
- `selected_uuids`: optional subset to target for planning.
- `mode`: string hint (e.g. "suggest", "optimize", "resolve_conflicts").
- `constraints`: optional `AiConstraints` (horizon/workhours/snap overrides).
- `model_id`, `seed`: optional metadata for deterministic planning.

## Outputs

Use `scalpel.ai.AiPlanResult`:

- `overrides`: dict of `{uuid: PlanOverride}` where each override specifies
  `start_ms`, `due_ms` (UTC epoch ms), and optional `duration_min`.
- `added_tasks`: list of new task dicts (must include `uuid`, `description`, `status`; `tags` must be a list when provided).
- `task_updates`: patch dict per uuid (merged into existing tasks).
- `warnings`, `notes`: planner messages (non-fatal).
- `model_id`: echoed for traceability.

## Validation

`scalpel.ai.validate_plan_overrides(payload, overrides)` enforces:
- UUIDs must exist in the payload.
- start/due must be ints and due > start.
- minute alignment (delta_ms % 60000 == 0).
- optional duration_min consistency.

## Integration Points

Recommended flow:

1) `payload = scalpel.payload.build_payload(...)`
2) `payload = scalpel.schema.upgrade_payload(payload)` (for schema invariants)
3) `plan = planner.plan(AiPlanRequest(payload=payload, ...))`
4) `validate_plan_overrides(payload, plan.overrides)`
5) `payload = scalpel.ai.apply_plan_overrides(payload, plan.overrides)`

This keeps AI changes isolated while preserving the core payload/render contract.

For task adds/updates:

```python
payload = scalpel.ai.apply_plan_result(payload, plan)
```

## Overrides JSON Format

Planner overrides are stored as JSON:

```json
{
  "uuid-1": {"start_ms": 1700000000000, "due_ms": 1700003600000, "duration_min": 60},
  "uuid-2": {"start_ms": 1700007200000, "due_ms": 1700010800000}
}
```

Accepted by:
- `scalpel` via `--plan-overrides`
- `scalpel-render-payload` via `--plan-overrides`

## Plan Result JSON Format

```json
{
  "schema": "scalpel.plan.v1",
  "overrides": {
    "uuid-1": {"start_ms": 1700000000000, "due_ms": 1700003600000, "duration_min": 60}
  },
  "added_tasks": [
    {"uuid": "new-uuid-1", "description": "New task", "status": "pending", "tags": []}
  ],
  "task_updates": {
    "uuid-1": {"description": "Updated title"}
  },
  "warnings": [],
  "notes": [],
  "model_id": "local-model-v1"
}
```

Accepted by:
- `scalpel` via `--plan-result`
- `scalpel-render-payload` via `--plan-result`

Plan result validation:
- `scalpel.ai.validate_plan_result(plan_dict)` returns a list of errors (empty means OK).
