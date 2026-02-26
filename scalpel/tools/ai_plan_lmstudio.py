#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

import datetime as dt

from scalpel.ai import load_plan_overrides, validate_plan_result
from scalpel.ai.slots import build_candidate_slots
from scalpel.util.tz import normalize_tz_name, resolve_tz
from scalpel.schema import upgrade_payload


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-ai-plan-lmstudio] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def _load_selected(path: Path) -> List[str]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, list):
        raise ValueError("selected uuids must be a JSON list")
    out: List[str] = []
    for u in obj:
        if isinstance(u, str) and u.strip():
            out.append(u.strip())
    return out


def _extract_tasks(payload: Dict[str, Any], selected: List[str]) -> List[Dict[str, Any]]:
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return []
    sel = set(selected)
    out: List[Dict[str, Any]] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        u = t.get("uuid")
        if not isinstance(u, str) or u not in sel:
            continue
        out.append(
            {
                "uuid": u,
                "description": t.get("description"),
                "status": t.get("status"),
                "project": t.get("project"),
                "tags": t.get("tags"),
                "scheduled_ms": t.get("scheduled_ms"),
                "due_ms": t.get("due_ms"),
                "duration_min": t.get("duration_min"),
                "start_calc_ms": t.get("start_calc_ms"),
                "end_calc_ms": t.get("end_calc_ms"),
            }
        )
    return out


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("No JSON object found in model output")
    try:
        obj = json.loads(m.group(0))
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from model output: {e}")
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON must be an object")
    return obj


def _build_prompt_v1(payload: Dict[str, Any], selected: List[str], user_prompt: str) -> str:
    cfg = payload.get("cfg") if isinstance(payload.get("cfg"), dict) else {}
    tasks = _extract_tasks(payload, selected)
    return json.dumps(
        {
            "instruction": (
                "Return ONLY a JSON object (no markdown) matching the plan result schema. "
                "Use schema 'scalpel.plan.v1'. Provide overrides for selected tasks, optional added_tasks, and task_updates. "
                "Do not modify tasks outside selected_uuids unless you add new tasks. "
                "Times are epoch ms."
            ),
            "schema": "scalpel.plan.v1",
            "selected_uuids": selected,
            "cfg": {
                "tz": cfg.get("tz"),
                "work_start_min": cfg.get("work_start_min"),
                "work_end_min": cfg.get("work_end_min"),
                "snap_min": cfg.get("snap_min"),
                "default_duration_min": cfg.get("default_duration_min"),
                "max_infer_duration_min": cfg.get("max_infer_duration_min"),
            },
            "tasks": tasks,
            "user_prompt": user_prompt or "",
        },
        ensure_ascii=False,
        indent=2,
    )


# Backwards-compatible alias used by contract tests and external scripts.
def _build_prompt(payload: Dict[str, Any], selected: List[str], user_prompt: str) -> str:
    return _build_prompt_v1(payload, selected, user_prompt)


def _build_prompt_v2(
    payload: Dict[str, Any],
    selected: List[str],
    user_prompt: str,
    *,
    max_slots_per_task: int,
) -> Tuple[str, Dict[str, Dict[str, int]]]:
    cfg = payload.get("cfg") if isinstance(payload.get("cfg"), dict) else {}
    tz_name = normalize_tz_name(cfg.get("tz") if isinstance(cfg.get("tz"), str) else "local")
    tz = resolve_tz(tz_name)
    now_iso = dt.datetime.now(tz=tz).replace(second=0, microsecond=0).isoformat(timespec="minutes")

    tasks = _extract_tasks(payload, selected)
    candidates_by_uuid, slot_catalog = build_candidate_slots(
        payload,
        selected,
        max_slots_per_task=int(max_slots_per_task),
    )

    candidates_compact: Dict[str, Any] = {}
    for u in selected:
        slots = candidates_by_uuid.get(u, [])
        candidates_compact[u] = [
            {
                "slot_id": s.slot_id,
                "start_iso": s.start_iso,
                "due_iso": s.due_iso,
                "day_key": s.day_key,
            }
            for s in slots
        ]

    prompt_obj = {
        "instruction": (
            "Return ONLY a JSON object (no markdown). Use schema 'scalpel.plan.v2'. "
            "Do NOT do time math. Select from provided slot_id values for placements. "
            "For each selected task, emit a place op: {op:'place', target:<uuid>, slot_id:<slot_id>}. "
            "To create a new task, emit create_task (with temp_id) then place it using the same temp_id in target."
        ),
        "schema": "scalpel.plan.v2",
        "now_iso": now_iso,
        "tz": tz_name,
        "selected_uuids": selected,
        "cfg": {
            "work_start_min": cfg.get("work_start_min"),
            "work_end_min": cfg.get("work_end_min"),
            "snap_min": cfg.get("snap_min"),
            "default_duration_min": cfg.get("default_duration_min"),
            "max_infer_duration_min": cfg.get("max_infer_duration_min"),
            "days": cfg.get("days"),
        },
        "tasks": tasks,
        "slot_candidates_by_uuid": candidates_compact,
        "user_prompt": user_prompt or "",
        "output_example": {
            "schema": "scalpel.plan.v2",
            "ops": [
                {"op": "place", "target": "<uuid>", "slot_id": "<slot_id>"},
                {
                    "op": "create_task",
                    "temp_id": "t1",
                    "description": "New task",
                    "duration_min": 30,
                },
                {"op": "place", "target": "t1", "slot_id": "<slot_id>"},
            ],
            "warnings": [],
            "notes": [],
        },
    }

    return json.dumps(prompt_obj, ensure_ascii=False, indent=2), slot_catalog


def _post_json(url: str, body: Dict[str, Any], api_key: Optional[str]) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    t0 = time.monotonic()
    try:
        with request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        body_txt = ""
        try:
            body_txt = e.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body_txt = ""
        suffix = f" body={body_txt[:400]!r}" if body_txt else ""
        raise RuntimeError(f"LM Studio HTTP {e.code} after {elapsed_ms}ms.{suffix}") from e
    except error.URLError as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        raise RuntimeError(f"LM Studio connection error after {elapsed_ms}ms: {e}") from e

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    if not text.strip():
        raise ValueError(f"LM Studio returned empty response after {elapsed_ms}ms")
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("LM Studio response must be a JSON object")
    return obj


def _snap_ms(ms: int, snap_min: int) -> int:
    snap = max(1, int(snap_min)) * 60000
    return int(round(int(ms) / snap) * snap)


def _normalize_plan_overrides(plan_obj: Dict[str, Any], snap_min: int) -> None:
    overrides = plan_obj.get("overrides")
    if not isinstance(overrides, dict):
        return
    for uuid, raw in list(overrides.items()):
        if not isinstance(raw, dict):
            continue
        start_ms = raw.get("start_ms")
        due_ms = raw.get("due_ms")
        if not isinstance(start_ms, int) or not isinstance(due_ms, int):
            continue
        start_ms = _snap_ms(start_ms, snap_min)
        due_ms = _snap_ms(due_ms, snap_min)
        if due_ms <= start_ms:
            continue
        raw["start_ms"] = start_ms
        raw["due_ms"] = due_ms
        raw["duration_min"] = max(1, int((due_ms - start_ms) // 60000))


def _filter_overrides(plan_obj: Dict[str, Any], payload: Dict[str, Any]) -> None:
    overrides = plan_obj.get("overrides")
    if not isinstance(overrides, dict):
        return
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return
    valid = set()
    for t in tasks:
        if isinstance(t, dict):
            u = t.get("uuid")
            if isinstance(u, str) and u:
                valid.add(u)
    drop = [k for k in overrides.keys() if k not in valid]
    for k in drop:
        overrides.pop(k, None)


def _plan_result_schema() -> Dict[str, Any]:
    return {
        "name": "scalpel_plan_v1",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "schema": {"type": "string", "const": "scalpel.plan.v1"},
                "overrides": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "start_ms": {"type": "integer"},
                            "due_ms": {"type": "integer"},
                            "duration_min": {"type": ["integer", "null"]},
                        },
                        "required": ["start_ms", "due_ms"],
                    },
                },
                "added_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "uuid": {"type": "string"},
                            "description": {"type": "string"},
                            "status": {"type": "string"},
                            "tags": {"type": "array"},
                        },
                        "required": ["uuid", "description", "status"],
                    },
                },
                "task_updates": {"type": "object", "additionalProperties": {"type": "object"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "array", "items": {"type": "string"}},
                "model_id": {"type": ["string", "null"]},
            },
            "required": ["schema", "overrides", "added_tasks", "task_updates", "warnings", "notes"],
        },
    }


def _plan_result_schema_v2() -> Dict[str, Any]:
    return {
        "name": "scalpel_plan_v2",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "schema": {"type": "string", "const": "scalpel.plan.v2"},
                "ops": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "op": {"type": "string"},
                        },
                        "required": ["op"],
                    },
                },
                "warnings": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "array", "items": {"type": "string"}},
                "model_id": {"type": ["string", "null"]},
            },
            "required": ["schema", "ops", "warnings", "notes"],
        },
    }


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-ai-plan-lmstudio",
        description="Local AI planner via LM Studio (OpenAI-compatible API).",
    )
    ap.add_argument("--in", dest="in_json", required=True, help="Input payload JSON path")
    ap.add_argument("--selected", required=True, help="JSON file with selected UUIDs array")
    ap.add_argument("--prompt", default="", help="User prompt")
    ap.add_argument("--out", required=True, help="Output plan result JSON path")
    ap.add_argument("--base-url", default="http://127.0.0.1:1234", help="LM Studio base URL")
    ap.add_argument("--model", default="ministral-3-14b-reasoning", help="Model name")
    ap.add_argument("--api-key", default=None, help="API key if required")
    ap.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    ap.add_argument("--max-tokens", type=int, default=1200, help="Max tokens for response")
    ap.add_argument("--overrides-in", default=None, help="Existing overrides JSON (optional)")
    ap.add_argument("--raw-out", default=None, help="Write raw model output to this path")
    ap.add_argument("--structured-output", action="store_true", help="Request JSON schema output (LM Studio)")
    ap.add_argument("--snap-min", type=int, default=0, help="Snap overrides to N minutes (default: cfg.snap_min)")
    ap.add_argument(
        "--plan-schema",
        choices=["v1", "v2"],
        default="v1",
        help="Plan schema to request from the model (default: v1)",
    )
    ap.add_argument(
        "--max-slots-per-task",
        type=int,
        default=24,
        help="Max candidate slots to include per task in v2 prompts (default: 24)",
    )
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_json)
    if not in_path.exists():
        return _die(f"Missing input JSON: {in_path}")

    try:
        payload_raw = _load_json(in_path)
        payload = upgrade_payload(payload_raw)
    except Exception as e:
        return _die(f"Failed to load JSON: {in_path} ({e})")

    try:
        selected = _load_selected(Path(ns.selected))
    except Exception as e:
        return _die(f"Failed to load selected uuids: {e}")

    slot_catalog: Dict[str, Dict[str, int]] = {}
    if ns.plan_schema == "v2":
        try:
            prompt, slot_catalog = _build_prompt_v2(
                payload,
                selected,
                ns.prompt,
                max_slots_per_task=int(ns.max_slots_per_task),
            )
        except ValueError as e:
            return _die(f"Invalid timezone value in payload/cfg: {e}")
    else:
        prompt = _build_prompt_v1(payload, selected, ns.prompt)

    body = {
        "model": ns.model,
        "messages": [
            {"role": "system", "content": "You are a scheduling assistant that outputs strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(ns.temperature),
        "max_tokens": int(ns.max_tokens),
    }
    if ns.structured_output:
        js = _plan_result_schema_v2() if ns.plan_schema == "v2" else _plan_result_schema()
        body["response_format"] = {"type": "json_schema", "json_schema": js}

    try:
        resp = _post_json(f"{ns.base_url.rstrip('/')}/v1/chat/completions", body, ns.api_key)
    except Exception as e:
        return _die(f"Request failed: {e}")

    try:
        choices = resp.get("choices")
        content = None
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(msg, dict):
                content = msg.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("No content in model response")
        if ns.raw_out:
            Path(ns.raw_out).write_text(content, encoding="utf-8")
        plan_obj = _extract_json_from_text(content)
    except Exception as e:
        if ns.raw_out and isinstance(locals().get("content"), str):
            try:
                Path(ns.raw_out).write_text(content, encoding="utf-8")
            except Exception:
                pass
        return _die(f"Failed to parse model output: {e}")

    if ns.plan_schema == "v2":
        # Attach engine slot catalog so v2 plans can be compiled without payload context.
        if slot_catalog:
            existing = plan_obj.get("slot_catalog")
            if isinstance(existing, dict):
                merged = dict(existing)
                for k, v in slot_catalog.items():
                    merged.setdefault(k, v)
                plan_obj["slot_catalog"] = merged
            else:
                plan_obj["slot_catalog"] = slot_catalog
    else:
        # Filter overrides to known task uuids.
        _filter_overrides(plan_obj, payload)

        # Snap overrides to minute boundaries.
        snap_min = int(ns.snap_min) if int(ns.snap_min) > 0 else int(payload.get("cfg", {}).get("snap_min") or 1)
        _normalize_plan_overrides(plan_obj, snap_min)

        # Merge existing overrides if provided.
        if ns.overrides_in:
            try:
                overrides = load_plan_overrides(Path(ns.overrides_in))
                ov = plan_obj.get("overrides") if isinstance(plan_obj.get("overrides"), dict) else {}
                merged = dict(ov)
                for k, v in overrides.items():
                    merged[k] = {"start_ms": v.start_ms, "due_ms": v.due_ms, "duration_min": v.duration_min}
                plan_obj["overrides"] = merged
            except Exception as e:
                return _die(f"Failed to merge overrides: {e}")

    errs = validate_plan_result(plan_obj)
    if errs:
        return _die("Invalid plan result:\n" + "\n".join(f"  - {e}" for e in errs), rc=3)

    out_path = Path(ns.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
