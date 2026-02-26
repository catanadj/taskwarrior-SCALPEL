# AI Planning Flow (End-to-End)

This is a deterministic, local flow you can run today using the stub planner.

## 1) Generate a payload

```bash
python3 -m scalpel.cli --no-open --out build/scalpel.html
python3 -m scalpel.tools.validate_payload --from-html build/scalpel.html --write-json build/payload.json
```

## 2) Select tasks

Create a JSON list of UUIDs:

```bash
python3 - <<'PY'
import json
from pathlib import Path
Path("build/selected.json").write_text(json.dumps(["<uuid1>", "<uuid2>"], indent=2))
PY
```

## 3) Run stub planner

The stub planner can emit either the legacy plan result format (v1) or the op-based
format (v2). v2 is the preferred format for local models because it avoids time
arithmetic in the model.

```bash
# v1 (legacy)
python3 -m scalpel.tools.ai_plan_stub \
  --in build/payload.json \
  --selected build/selected.json \
  --prompt "align starts" \
  --plan-schema v1 \
  --out build/plan.json

# v2 (op-based; preferred)
python3 -m scalpel.tools.ai_plan_stub \
  --in build/payload.json \
  --selected build/selected.json \
  --prompt "align starts" \
  --plan-schema v2 \
  --out build/plan.json
```

## 3b) Run LM Studio planner (optional)

LM Studio planning defaults to plan schema v1 (legacy). Use v2 for local models.

```bash
python3 -m scalpel.tools.ai_plan_lmstudio \
  --in build/payload.json \
  --selected build/selected.json \
  --prompt "align starts" \
  --out build/plan.json \
  --base-url http://127.0.0.1:1234 \
  --model ministral-3-14b-reasoning
```

Notes:
  - Use `--plan-schema v2` for op-based planning.
  - v2 prompts include engine-generated candidate slots; the model should only pick `slot_id` values.

## 4) Apply plan + render

```bash
python3 -m scalpel.tools.apply_plan_result \
  --in build/payload.json \
  --plan build/plan.json \
  --out build/payload_planned.json

python3 -m scalpel.tools.render_payload \
  --in build/payload_planned.json \
  --out build/scalpel_planned.html
```
