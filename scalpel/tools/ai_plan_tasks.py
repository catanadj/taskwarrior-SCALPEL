#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import sys
import uuid as uuidlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request
from urllib.error import HTTPError

from scalpel.goals import load_goals_config
from scalpel.taskwarrior import run_task_export


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-ai-plan-tasks] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, list):
        raise ValueError("export must be a JSON list")
    return [t for t in obj if isinstance(t, dict)]


def _task_uuid(t: Dict[str, Any]) -> Optional[str]:
    u = t.get("uuid")
    if isinstance(u, str) and u.strip():
        return u.strip()
    return None


def _project_match(project: str, prefixes: List[str]) -> bool:
    if not project:
        return False
    for p in prefixes:
        if project.startswith(p):
            return True
    return False


def _goal_match(task: Dict[str, Any], goal: Dict[str, Any]) -> bool:
    project = str(task.get("project") or "")
    tags = task.get("tags") if isinstance(task.get("tags"), list) else []
    tags = [str(x) for x in tags if str(x).strip()]

    projects = goal.get("projects") or []
    tags_any = goal.get("tags") or []
    tags_all = goal.get("tags_all") or []
    mode = goal.get("mode") or "any"

    checks = []
    if projects:
        checks.append(_project_match(project, projects))
    if tags_any:
        checks.append(any(t in tags for t in tags_any))
    if tags_all:
        checks.append(all(t in tags for t in tags_all))

    if not checks:
        return False
    if mode == "all":
        return all(checks)
    return any(checks)


def _select_tasks(
    tasks: List[Dict[str, Any]],
    *,
    filter_uuids: Optional[set[str]] = None,
    projects: Optional[List[str]] = None,
    goal: Optional[Dict[str, Any]] = None,
    include_done: bool = False,
) -> List[Dict[str, Any]]:
    out = []
    for t in tasks:
        u = _task_uuid(t)
        if not u:
            continue
        if not include_done:
            st = str(t.get("status") or "").lower()
            if st in {"completed", "deleted"}:
                continue
        if filter_uuids is not None and u not in filter_uuids:
            continue
        if projects:
            proj = str(t.get("project") or "")
            if not _project_match(proj, projects):
                continue
        if goal and not _goal_match(t, goal):
            continue
        out.append(t)
    return out


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("No JSON object found in model output")
    raw = text[start : end + 1]
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON must be an object")
    return obj


def _post_json(url: str, body: Dict[str, Any], api_key: Optional[str]) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        raise ValueError(f"HTTP {e.code} error: {raw}") from e
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("LM Studio response must be a JSON object")
    return obj


def _iso_to_tw_utc(s: str) -> str:
    raw = s.strip().replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(raw)
    if d.tzinfo is None:
        raise ValueError(f"ISO time must include timezone offset: {s!r}")
    d = d.astimezone(dt.timezone.utc)
    return d.strftime("%Y%m%dT%H%M%SZ")


def _apply_ops(
    tasks: List[Dict[str, Any]],
    ops: List[Dict[str, Any]],
    *,
    default_project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    tasks_by_uuid = {t.get("uuid"): t for t in tasks if isinstance(t.get("uuid"), str)}
    temp_map: Dict[str, str] = {}

    def resolve_target(raw: Any) -> Optional[str]:
        if not isinstance(raw, str) or not raw.strip():
            return None
        s = raw.strip()
        if s in temp_map:
            return temp_map[s]
        if len(s) == 8:
            matches = [u for u in tasks_by_uuid.keys() if isinstance(u, str) and u.startswith(s)]
            if len(matches) == 1:
                return matches[0]
        return s

    for op in ops:
        if not isinstance(op, dict):
            continue
        kind = str(op.get("op") or "").strip()
        if kind == "create_task":
            temp_id = str(op.get("temp_id") or "").strip()
            desc = str(op.get("description") or "").strip()
            if not temp_id or not desc:
                continue
            u = str(op.get("uuid") or "").strip() or str(uuidlib.uuid4())
            temp_map[temp_id] = u
            t: Dict[str, Any] = {
                "uuid": u,
                "description": desc,
                "status": str(op.get("status") or "pending"),
            }
            if isinstance(op.get("project"), str) and op.get("project").strip():
                t["project"] = str(op.get("project")).strip()
            elif default_project:
                t["project"] = default_project
            tags = op.get("tags")
            if isinstance(tags, list):
                t["tags"] = [str(x) for x in tags if str(x).strip()]
            for k in ("due_iso", "scheduled_iso"):
                if isinstance(op.get(k), str) and op.get(k).strip():
                    tw = _iso_to_tw_utc(str(op.get(k)))
                    t[k.replace("_iso", "")] = tw
            tasks_by_uuid[u] = t
        elif kind == "update_task":
            target = resolve_target(op.get("uuid") or op.get("target"))
            patch = op.get("patch")
            if not target or not isinstance(patch, dict):
                continue
            base = tasks_by_uuid.get(target)
            if not isinstance(base, dict):
                continue
            for k, v in patch.items():
                if k in ("uuid", "target"):
                    continue
                if k in ("due_iso", "scheduled_iso") and isinstance(v, str) and v.strip():
                    base[k.replace("_iso", "")] = _iso_to_tw_utc(v)
                    continue
                base[k] = v
        elif kind == "complete_task":
            target = resolve_target(op.get("uuid") or op.get("target"))
            if target and target in tasks_by_uuid:
                tasks_by_uuid[target]["status"] = "completed"
        elif kind == "delete_task":
            target = resolve_target(op.get("uuid") or op.get("target"))
            if target and target in tasks_by_uuid:
                tasks_by_uuid[target]["status"] = "deleted"

    return list(tasks_by_uuid.values())


def _summarize_ops(ops: List[Dict[str, Any]], tasks_by_uuid: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    counts: Dict[str, int] = {}
    lines: List[str] = []
    for op in ops:
        if not isinstance(op, dict):
            continue
        kind = str(op.get("op") or "").strip() or "unknown"
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "update_task":
            target = op.get("uuid") or op.get("target") or ""
            if tasks_by_uuid and target not in tasks_by_uuid and isinstance(target, str) and len(target) == 8:
                matches = [u for u in tasks_by_uuid.keys() if isinstance(u, str) and u.startswith(target)]
                if len(matches) == 1:
                    target = matches[0]
            patch = op.get("patch") if isinstance(op.get("patch"), dict) else {}
            keys = ", ".join(sorted(str(k) for k in patch.keys())) if patch else ""
            preview = ""
            if isinstance(patch.get("description"), str):
                new_desc = patch.get("description")
                old_desc = None
                if tasks_by_uuid and target in tasks_by_uuid:
                    old_desc = tasks_by_uuid[target].get("description")
                if isinstance(old_desc, str) and old_desc != new_desc:
                    preview = f' desc: "{old_desc}" -> "{new_desc}"'
                else:
                    preview = f' desc="{new_desc}"'
            if "tags" in patch:
                new_tags = patch.get("tags")
                old_tags = None
                if tasks_by_uuid and target in tasks_by_uuid:
                    old_tags = tasks_by_uuid[target].get("tags")
                if old_tags != new_tags:
                    preview += f" tags: {old_tags!r} -> {new_tags!r}"
            lines.append(f"- update_task {target} ({keys}){preview}")
        elif kind == "create_task":
            desc = str(op.get("description") or "").strip()
            lines.append(f"- create_task {desc}")
        elif kind in ("complete_task", "delete_task"):
            target = op.get("uuid") or op.get("target") or ""
            lines.append(f"- {kind} {target}")
    head = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
    detail = "\n".join(lines[:12])
    return head + ("\n" + detail if detail else "")


def _diff_summary(before: List[Dict[str, Any]], after: List[Dict[str, Any]]) -> str:
    bmap = {t.get("uuid"): t for t in before if isinstance(t.get("uuid"), str)}
    amap = {t.get("uuid"): t for t in after if isinstance(t.get("uuid"), str)}

    added = [u for u in amap.keys() if u not in bmap]
    updated = []
    completed = []
    deleted = []

    for u, a in amap.items():
        b = bmap.get(u)
        if not b:
            continue
        if a != b:
            updated.append(u)
        bstat = str(b.get("status") or "")
        astat = str(a.get("status") or "")
        if astat == "completed" and bstat != "completed":
            completed.append(u)
        if astat == "deleted" and bstat != "deleted":
            deleted.append(u)

    def _short(u: str) -> str:
        return str(u)[:8]

    parts = [
        f"added: {len(added)}",
        f"updated: {len(updated)}",
        f"completed: {len(completed)}",
        f"deleted: {len(deleted)}",
    ]
    detail = []
    if added:
        detail.append("added: " + ", ".join(_short(u) for u in added[:6]))
    if updated:
        detail.append("updated: " + ", ".join(_short(u) for u in updated[:6]))
    if completed:
        detail.append("completed: " + ", ".join(_short(u) for u in completed[:6]))
    if deleted:
        detail.append("deleted: " + ", ".join(_short(u) for u in deleted[:6]))
    return ", ".join(parts) + ("\n" + "\n".join(detail) if detail else "")


def _diff_preview(before: List[Dict[str, Any]], after: List[Dict[str, Any]], limit: int = 6) -> str:
    bmap = {t.get("uuid"): t for t in before if isinstance(t.get("uuid"), str)}
    lines: List[str] = []
    for t in after:
        u = t.get("uuid")
        if not isinstance(u, str):
            continue
        b = bmap.get(u)
        if b is None:
            desc = t.get("description")
            lines.append(f"+ {u[:8]} desc={desc!r}")
            if len(lines) >= limit:
                break
            continue
        if b == t:
            continue
        for key in ("description", "project", "tags", "status", "due", "scheduled"):
            bv = b.get(key)
            av = t.get(key)
            if bv != av:
                lines.append(f"* {u[:8]} {key}: {bv!r} -> {av!r}")
                if len(lines) >= limit:
                    break
        if len(lines) >= limit:
            break
    return "\n".join(lines)


def _diff_tasks(before: List[Dict[str, Any]], after: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    bmap = {t.get("uuid"): t for t in before if isinstance(t.get("uuid"), str)}
    out = []
    for t in after:
        u = t.get("uuid")
        if not isinstance(u, str):
            continue
        b = bmap.get(u)
        if b is None or b != t:
            out.append(t)
    return out


def _selection_summary(tasks: List[Dict[str, Any]]) -> str:
    total = len(tasks)
    by_status: Dict[str, int] = {}
    by_project: Dict[str, int] = {}
    by_tag: Dict[str, int] = {}
    for t in tasks:
        st = str(t.get("status") or "unknown").lower()
        by_status[st] = by_status.get(st, 0) + 1
        proj = str(t.get("project") or "").strip() or "(none)"
        by_project[proj] = by_project.get(proj, 0) + 1
        tags = t.get("tags") if isinstance(t.get("tags"), list) else []
        for tag in tags[:20]:
            tag_s = str(tag).strip()
            if tag_s:
                by_tag[tag_s] = by_tag.get(tag_s, 0) + 1
    top_projects = ", ".join(f"{k}:{v}" for k, v in sorted(by_project.items(), key=lambda x: -x[1])[:5])
    top_tags = ", ".join(f"{k}:{v}" for k, v in sorted(by_tag.items(), key=lambda x: -x[1])[:5])
    statuses = ", ".join(f"{k}:{v}" for k, v in sorted(by_status.items(), key=lambda x: -x[1])[:5])
    return (
        f"total: {total}\n"
        f"status: {statuses or 'n/a'}\n"
        f"projects: {top_projects or 'n/a'}\n"
        f"tags: {top_tags or 'n/a'}"
    )


def _update_summary(summary: str, user_prompt: str, plan_obj: Dict[str, Any], max_len: int) -> str:
    lines = []
    if summary:
        lines.append(summary.strip())
    lines.append(f"User: {user_prompt.strip()}")
    ops = plan_obj.get("ops") if isinstance(plan_obj.get("ops"), list) else []
    lines.append(f"Model ops: {len(ops)}")
    warnings = plan_obj.get("warnings") if isinstance(plan_obj.get("warnings"), list) else []
    notes = plan_obj.get("notes") if isinstance(plan_obj.get("notes"), list) else []
    if warnings:
        lines.append("Warnings: " + "; ".join(str(w) for w in warnings[:3]))
    if notes:
        lines.append("Notes: " + "; ".join(str(n) for n in notes[:3]))
    out = " | ".join(lines)
    if len(out) > max_len:
        out = out[-max_len:]
    return out


def _normalize_ops(ops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for op in ops:
        if not isinstance(op, dict):
            continue
        kind = str(op.get("op") or "").strip()
        if kind == "update_task":
            patch = op.get("patch") if isinstance(op.get("patch"), dict) else None
            if not patch:
                patch = {
                    k: v
                    for k, v in op.items()
                    if k not in ("op", "uuid", "target", "temp_id")
                }
            if not patch:
                continue
            op = dict(op)
            op["patch"] = patch
        out.append(op)
    return out


def _taskplan_schema() -> Dict[str, Any]:
    return {
        "name": "scalpel_taskplan_v1",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "schema": {"type": "string", "const": "scalpel.taskplan.v1"},
                "ops": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "op": {
                                "type": "string",
                                "enum": ["create_task", "update_task", "complete_task", "delete_task"],
                            }
                        },
                        "required": ["op"],
                    },
                },
                "response": {"type": "string"},
                "clarifying_questions": {"type": "array", "items": {"type": "string"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "object"},
                "confidence": {"type": "number"},
                "ambiguities": {"type": "array", "items": {"type": "string"}},
                "suggestions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["schema", "ops"],
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-ai-plan-tasks",
        description="AI task planner: propose task create/update ops from Taskwarrior export.",
    )
    ap.add_argument("--in-export", default=None, help="Taskwarrior export JSON path (optional)")
    ap.add_argument("--filter", default=None, help="Taskwarrior filter (live export only)")
    ap.add_argument("--project", action="append", default=[], help="Project prefix filter (repeatable)")
    ap.add_argument("--goal", default=None, help="Goal id (from goals config)")
    ap.add_argument("--goal-project", action="append", default=[], help="Restrict goal to project prefixes")
    ap.add_argument("--goal-tag", action="append", default=[], help="Restrict goal to tags (any)")
    ap.add_argument("--goal-tag-all", action="append", default=[], help="Restrict goal to tags (all)")
    ap.add_argument("--goals-config", default="scalpel/goals.json", help="Goals config JSON path")
    ap.add_argument("--prompt", default="", help="User prompt for planning")
    ap.add_argument("--new-project", action="store_true", help="Plan for a new project (no existing tasks)")
    ap.add_argument("--include-done", action="store_true", help="Include completed/deleted tasks in selection")
    ap.add_argument("--out", required=True, help="Write Taskwarrior import JSON to this path")
    ap.add_argument(
        "--out-mode",
        choices=["selected", "delta", "full"],
        default="selected",
        help="Output tasks: selected (default), delta (changed only), or full",
    )
    ap.add_argument("--max-change", type=int, default=50, help="Confirm if more than N tasks change")
    ap.add_argument("--print-payload", action="store_true", help="Print model payload JSON and exit")
    ap.add_argument("--interactive", action="store_true", help="Interactive planning session")
    ap.add_argument("--summary-max-chars", type=int, default=1200, help="Max chars for rolling summary")
    ap.add_argument("--max-prompt-chars", type=int, default=9000, help="Max chars for model prompt JSON")
    ap.add_argument("--max-selected", type=int, default=60, help="Max tasks to include in model context")
    ap.add_argument("--max-ops", type=int, default=5, help="Max ops to propose in one response")
    ap.add_argument("--min-confidence", type=float, default=0.6, help="Minimum confidence to accept ops")
    ap.add_argument("--base-url", default="http://127.0.0.1:1234", help="LM Studio base URL")
    ap.add_argument("--model", default="ministral-3-14b-reasoning", help="Model name")
    ap.add_argument("--api-key", default=None, help="API key if required")
    ap.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    ap.add_argument("--max-tokens", type=int, default=1500, help="Max tokens for response")
    ap.add_argument("--structured-output", action="store_true", help="Request JSON schema output")
    ns = ap.parse_args(argv)

    if ns.in_export and ns.filter:
        return _die("--filter requires live export (omit --in-export)")

    if ns.in_export:
        try:
            tasks_full = _load_json_list(Path(ns.in_export))
        except Exception as e:
            return _die(f"Failed to load export JSON: {e}")
        filter_uuids = None
        base_tasks = list(tasks_full)
    else:
        tasks_full = run_task_export("")
        filter_uuids = None
        if ns.filter and ns.filter.strip():
            filtered = run_task_export(ns.filter)
            filter_uuids = {u for u in (_task_uuid(t) for t in filtered) if u}
        base_tasks = list(tasks_full)

    goal = None
    if ns.goal:
        goals_cfg = load_goals_config(ns.goals_config)
        if not goals_cfg or not goals_cfg.get("goals"):
            return _die(f"Goal config not found or empty: {ns.goals_config}")
        for g in goals_cfg["goals"]:
            if g.get("id") == ns.goal:
                goal = dict(g)
                break
        if goal is None:
            return _die(f"Goal not found: {ns.goal}")

        if ns.goal_project:
            goal["projects"] = [p for p in goal.get("projects", []) if any(p.startswith(x) for x in ns.goal_project)]
        if ns.goal_tag:
            goal["tags"] = [t for t in goal.get("tags", []) if t in ns.goal_tag]
        if ns.goal_tag_all:
            goal["tags_all"] = [t for t in goal.get("tags_all", []) if t in ns.goal_tag_all]

    if ns.new_project:
        selected = []
    else:
        selected = _select_tasks(
            tasks_full,
            filter_uuids=filter_uuids,
            projects=ns.project if ns.project else None,
            goal=goal,
            include_done=ns.include_done,
        )
    if ns.max_selected and len(selected) > int(ns.max_selected):
        selected = selected[: int(ns.max_selected)]

    if not selected and not ns.new_project:
        return _die("No tasks matched the selection criteria")

    selected_uuids = [u for u in (_task_uuid(t) for t in selected) if u]
    short_map: Dict[str, str] = {}
    full_map: Dict[str, str] = {}
    for u in selected_uuids:
        s = str(u)[:8]
        if s in short_map and short_map[s] != u:
            short_map = {}
            full_map = {}
            break
        short_map[s] = u
        full_map[u] = s
    tasks_payload = []
    for t in selected:
        u = t.get("uuid")
        if not isinstance(u, str):
            continue
        uid = full_map.get(u, u)
        tasks_payload.append(
            {
                "uuid": uid,
                "description": t.get("description"),
                "project": t.get("project"),
                "tags": t.get("tags"),
            }
        )

    summary = ""
    print("Selection summary:")
    print(_selection_summary(selected))

    def _build_prompt_obj(user_prompt: str, summary_text: str) -> Dict[str, Any]:
        def build_tasks(minimal: bool, limit: Optional[int]) -> List[Dict[str, Any]]:
            items = tasks_payload[: limit or len(tasks_payload)]
            out = []
            for t in items:
                base = {
                    "uuid": t.get("uuid"),
                    "description": t.get("description"),
                    "project": t.get("project"),
                    "tags": t.get("tags"),
                }
                if minimal:
                    out.append(base)
                else:
                    out.append(base)
            return out

        base = {
            "instruction": (
                "Return ONLY JSON matching schema 'scalpel.taskplan.v1'. "
                "Allowed ops: create_task, update_task, complete_task, delete_task. "
                "Use keys: schema, ops. Do NOT use 'operations'. "
                "You may also include response, clarifying_questions, ambiguities, suggestions, confidence. "
                "Use update_task only for uuids in selected_uuids. "
                "For create_task include temp_id and description (project/tags/status optional). "
                "If you provide due_iso/scheduled_iso, include a timezone offset. "
                f"Do not propose more than {int(ns.max_ops)} ops. "
                "If the prompt is unclear or not actionable, return an empty ops list and include response or clarifying_questions. "
                "Include reasoning/confidence/ambiguities/suggestions when helpful."
            ),
            "schema": "scalpel.taskplan.v1",
            "selected_uuids": [full_map.get(u, u) for u in selected_uuids],
            "tasks": [],
            "user_prompt": user_prompt or "",
            "conversation_summary": summary_text or "",
            "uuid_format": "short" if full_map else "full",
            "uuid_short_len": 8 if full_map else 36,
            "max_ops": int(ns.max_ops),
            "mode": "new_project" if ns.new_project else "update_existing",
            "default_project": ns.project[0] if ns.project else None,
        }
        max_chars = int(ns.max_prompt_chars)
        minimal = False
        limit: Optional[int] = None

        for _ in range(5):
            base["tasks"] = build_tasks(minimal, limit)
            text = json.dumps(base, ensure_ascii=False)
            if len(text) <= max_chars:
                break
            if not minimal:
                minimal = True
                continue
            if limit is None:
                limit = max(10, min(len(tasks_payload), 100))
            else:
                limit = max(10, int(limit * 0.7))
            base["tasks_truncated"] = True
            base["tasks_total"] = len(tasks_payload)
            base["tasks_limit"] = limit
        return base

    def run_round(user_prompt: str, summary_text: str) -> Dict[str, Any]:
        prompt_obj = _build_prompt_obj(user_prompt, summary_text)

        body = {
            "model": ns.model,
            "messages": [
                {"role": "system", "content": "You are a task planning assistant that outputs strict JSON only."},
                {"role": "user", "content": json.dumps(prompt_obj, ensure_ascii=False, indent=2)},
            ],
            "temperature": float(ns.temperature),
            "max_tokens": int(ns.max_tokens),
        }
        if ns.structured_output:
            body["response_format"] = {"type": "json_schema", "json_schema": _taskplan_schema()}

        resp = _post_json(f"{ns.base_url.rstrip('/')}/v1/chat/completions", body, ns.api_key)
        choices = resp.get("choices")
        content = None
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(msg, dict):
                content = msg.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("No content in model response")
        plan_obj = _extract_json_from_text(content)
        if "schema" not in plan_obj and isinstance(plan_obj.get("operations"), list):
            plan_obj = {"schema": "scalpel.taskplan.v1", "ops": plan_obj.get("operations")}
        return plan_obj

    if ns.print_payload:
        payload = _build_prompt_obj(ns.prompt or "", summary)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    default_project = ns.project[0] if ns.project else None

    if not ns.interactive:
        try:
            plan_obj = run_round(ns.prompt or "", summary)
        except Exception as e:
            return _die(f"Request failed: {e}")

        if plan_obj.get("schema") != "scalpel.taskplan.v1":
            return _die("Invalid schema in model output:\n" + json.dumps(plan_obj, indent=2))
        ops = plan_obj.get("ops")
        if not isinstance(ops, list):
            return _die("Model output missing ops list")
        ops = _normalize_ops(ops)
        plan_obj = dict(plan_obj)
        plan_obj["ops"] = ops
        ambiguities = plan_obj.get("ambiguities") if isinstance(plan_obj.get("ambiguities"), list) else []
        confidence = plan_obj.get("confidence")
        response = plan_obj.get("response") if isinstance(plan_obj.get("response"), str) else None
        clar_qs = plan_obj.get("clarifying_questions") if isinstance(plan_obj.get("clarifying_questions"), list) else []
        if not ops and (response or clar_qs):
            if response:
                print(response)
            if clar_qs:
                print("\nClarifying questions:")
                for q in clar_qs:
                    print(f"- {q}")
            out_path = Path(ns.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]\n", encoding="utf-8")
            return 0
        if ambiguities or (isinstance(confidence, (int, float)) and confidence < ns.min_confidence):
            return _die("Model response requires clarification; rerun in interactive mode.")

        try:
            if ns.out_mode == "full":
                before_full = copy.deepcopy(list(tasks_full))
                merged = _apply_ops(list(tasks_full), ops, default_project=default_project)
                out_tasks = merged
            else:
                before_sel = copy.deepcopy(list(selected))
                merged = _apply_ops(list(selected), ops, default_project=default_project)
                if ns.out_mode == "delta":
                    out_tasks = _diff_tasks(before_sel, merged)
                else:
                    out_tasks = merged
        except Exception as e:
            return _die(f"Failed to apply ops: {e}")

        out_path = Path(ns.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out_tasks, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0

    last_plan: Optional[Dict[str, Any]] = None
    initial_prompt = (ns.prompt or "").strip()
    if initial_prompt:
        try:
            plan_obj = run_round(initial_prompt, summary)
        except Exception as e:
            print(f"Request failed: {e}")
            plan_obj = None
        if plan_obj:
            if plan_obj.get("schema") != "scalpel.taskplan.v1":
                print("Invalid schema in model output")
                print(json.dumps(plan_obj, indent=2))
            else:
                ops = plan_obj.get("ops") if isinstance(plan_obj.get("ops"), list) else []
                ops = _normalize_ops(ops)
                plan_obj = dict(plan_obj)
                plan_obj["ops"] = ops

                print("\nOps summary:")
                tasks_map = {t.get("uuid"): t for t in tasks_full if isinstance(t.get("uuid"), str)}
                print(_summarize_ops(ops, tasks_map) or "(none)")

                warnings = plan_obj.get("warnings") if isinstance(plan_obj.get("warnings"), list) else []
                ambiguities = plan_obj.get("ambiguities") if isinstance(plan_obj.get("ambiguities"), list) else []
                suggestions = plan_obj.get("suggestions") if isinstance(plan_obj.get("suggestions"), list) else []
                response = plan_obj.get("response") if isinstance(plan_obj.get("response"), str) else None
                clar_qs = plan_obj.get("clarifying_questions") if isinstance(plan_obj.get("clarifying_questions"), list) else []
                confidence = plan_obj.get("confidence")

                if warnings:
                    print("\nWarnings:")
                    for w in warnings:
                        print(f"- {w}")
                if ambiguities:
                    print("\nAmbiguities:")
                    for a in ambiguities:
                        print(f"- {a}")
                if response:
                    print("\nResponse:\n" + response)
                if clar_qs:
                    print("\nClarifying questions:")
                    for q in clar_qs:
                        print(f"- {q}")
                if suggestions:
                    print("\nSuggestions:")
                    for s in suggestions:
                        print(f"- {s}")

                if not ops:
                    raw_ops = plan_obj.get("ops") if isinstance(plan_obj.get("ops"), list) else []
                    print("\nNo actionable ops. Refine the prompt.")
                    if raw_ops:
                        print("\nRaw ops (first 5):")
                        print(json.dumps(raw_ops[:5], indent=2))
                    else:
                        print("\nRaw plan:")
                        print(json.dumps(plan_obj, indent=2))
                elif ambiguities or (isinstance(confidence, (int, float)) and confidence < ns.min_confidence):
                    print("\nClarify required:")
                    for a in ambiguities:
                        print(f"- {a}")
                    clar = input("> ").strip()
                    if clar:
                        summary = _update_summary(summary, "clarify:" + clar, plan_obj, int(ns.summary_max_chars))
                else:
                    summary = _update_summary(summary, initial_prompt, plan_obj, int(ns.summary_max_chars))
                    last_plan = plan_obj
    while True:
        print("\nPrompt (or :accept / :quit):")
        try:
            user_prompt = input("> ").strip()
        except EOFError:
            return 0
        if not user_prompt:
            continue
        if user_prompt in (":quit", ":exit"):
            return 0
        if user_prompt == ":accept":
            if not last_plan:
                print("No plan to accept yet.")
                continue
            ops = last_plan.get("ops") if isinstance(last_plan.get("ops"), list) else []
            try:
                if ns.out_mode == "full":
                    before_full = copy.deepcopy(list(tasks_full))
                    merged = _apply_ops(list(tasks_full), ops, default_project=default_project)
                    out_tasks = merged
                else:
                    before_sel = copy.deepcopy(list(selected))
                    merged = _apply_ops(list(selected), ops, default_project=default_project)
                    if ns.out_mode == "delta":
                        out_tasks = _diff_tasks(before_sel, merged)
                    else:
                        out_tasks = merged
            except Exception as e:
                print(f"Failed to apply ops: {e}")
                continue
            base_for_diff = list(tasks_full) if ns.out_mode == "full" else list(selected)
            print("Diff:", _diff_summary(base_for_diff, merged))
            preview = _diff_preview(base_for_diff, merged, limit=6)
            if preview:
                print("\nPreview:\n" + preview)
            changed = len(_diff_tasks(base_for_diff, merged))
            if ns.max_change and changed > int(ns.max_change):
                print(f"\nChange count {changed} exceeds max-change {ns.max_change}.")
                confirm = input("Proceed anyway? [y/N]: ").strip().lower()
                if confirm != "y":
                    continue
            confirm = input("Write import JSON? [y/N]: ").strip().lower()
            if confirm != "y":
                continue
            out_path = Path(ns.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(out_tasks, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Wrote {ns.out}")
            return 0

        try:
            plan_obj = run_round(user_prompt, summary)
        except Exception as e:
            print(f"Request failed: {e}")
            continue

        if plan_obj.get("schema") != "scalpel.taskplan.v1":
            print("Invalid schema in model output")
            print(json.dumps(plan_obj, indent=2))
            continue
        ops = plan_obj.get("ops")
        if not isinstance(ops, list):
            print("Model output missing ops list")
            continue
        ops = _normalize_ops(ops)
        plan_obj = dict(plan_obj)
        plan_obj["ops"] = ops

        print("\nOps summary:")
        tasks_map = {t.get("uuid"): t for t in tasks_full if isinstance(t.get("uuid"), str)}
        print(_summarize_ops(ops, tasks_map) or "(none)")
        warnings = plan_obj.get("warnings") if isinstance(plan_obj.get("warnings"), list) else []
        ambiguities = plan_obj.get("ambiguities") if isinstance(plan_obj.get("ambiguities"), list) else []
        suggestions = plan_obj.get("suggestions") if isinstance(plan_obj.get("suggestions"), list) else []
        confidence = plan_obj.get("confidence")
        response = plan_obj.get("response") if isinstance(plan_obj.get("response"), str) else None
        clar_qs = plan_obj.get("clarifying_questions") if isinstance(plan_obj.get("clarifying_questions"), list) else []
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f"- {w}")
        if ambiguities:
            print("\nAmbiguities:")
            for a in ambiguities:
                print(f"- {a}")
        if response:
            print("\nResponse:\n" + response)
        if clar_qs:
            print("\nClarifying questions:")
            for q in clar_qs:
                print(f"- {q}")
        if suggestions:
            print("\nSuggestions:")
            for s in suggestions:
                print(f"- {s}")
        if not ops:
            raw_ops = plan_obj.get("ops") if isinstance(plan_obj.get("ops"), list) else []
            print("\nNo actionable ops. Refine the prompt.")
            if raw_ops:
                print("\nRaw ops (first 5):")
                print(json.dumps(raw_ops[:5], indent=2))
            else:
                print("\nRaw plan:")
                print(json.dumps(plan_obj, indent=2))
            continue
        if ambiguities or (isinstance(confidence, (int, float)) and confidence < ns.min_confidence):
            print("\nClarify required:")
            for a in ambiguities:
                print(f"- {a}")
            clar = input("> ").strip()
            if clar:
                summary = _update_summary(summary, "clarify:" + clar, plan_obj, int(ns.summary_max_chars))
            continue

        summary = _update_summary(summary, user_prompt, plan_obj, int(ns.summary_max_chars))
        last_plan = plan_obj


if __name__ == "__main__":
    raise SystemExit(main())
