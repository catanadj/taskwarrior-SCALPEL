from __future__ import annotations

import copy
from typing import Any, Dict, List
from uuid import NAMESPACE_DNS, uuid5

def _dt_to_ymd(s: Any) -> str | None:
    if not isinstance(s, str) or not s:
        return None
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None

def build_indices_v1(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_uuid: Dict[str, int] = {}
    by_status: Dict[str, List[int]] = {}
    by_project: Dict[str, List[int]] = {}
    by_tag: Dict[str, List[int]] = {}
    by_day: Dict[str, List[int]] = {}

    for i, t in enumerate(tasks):
        u = str(t.get("uuid") or "").strip()
        if u:
            by_uuid[u] = i

        st = str(t.get("status") or "").strip() or "unknown"
        by_status.setdefault(st, []).append(i)

        pr = t.get("project")
        if isinstance(pr, str) and pr.strip():
            by_project.setdefault(pr, []).append(i)

        tags = t.get("tags")
        if not isinstance(tags, list):
            tags = []
            t["tags"] = tags
        for tg in tags:
            if isinstance(tg, str) and tg.strip():
                by_tag.setdefault(tg, []).append(i)

        ymd = _dt_to_ymd(t.get("due")) or _dt_to_ymd(t.get("entry")) or _dt_to_ymd(t.get("modified"))
        if ymd:
            by_day.setdefault(ymd, []).append(i)

    for m in (by_status, by_project, by_tag, by_day):
        for k in list(m.keys()):
            m[k] = sorted(m[k])

    return {"by_uuid": by_uuid, "by_status": by_status, "by_project": by_project, "by_tag": by_tag, "by_day": by_day}

def make_large_payload_v1(base_payload: Dict[str, Any], *, n_tasks: int, seed: int = 1) -> Dict[str, Any]:
    if not isinstance(base_payload, dict):
        raise ValueError("base payload must be dict")
    base_tasks = base_payload.get("tasks")
    if not isinstance(base_tasks, list) or not base_tasks:
        raise ValueError("base payload missing non-empty 'tasks' list")

    out = copy.deepcopy(base_payload)

    tasks: List[Dict[str, Any]] = []
    src_n = len(base_tasks)

    project_pool = ["bench.alpha", "bench.beta", "bench.gamma", "bench.delta"]
    tag_pool = ["bench", "perf", "fixture", "golden"]

    for i in range(n_tasks):
        src = base_tasks[i % src_n]
        if not isinstance(src, dict):
            src = {}
        t = copy.deepcopy(src)

        base_uuid = str(t.get("uuid") or f"base-{i%src_n}")
        t["uuid"] = str(uuid5(NAMESPACE_DNS, f"scalpel.large.v1:{seed}:{i}:{base_uuid}"))

        if not isinstance(t.get("status"), str) or not t.get("status"):
            t["status"] = "pending"
        if not isinstance(t.get("tags"), list):
            t["tags"] = []

        if i % 7 == 0:
            t["status"] = "completed"
        elif i % 11 == 0:
            t["status"] = "deleted"
        else:
            t["status"] = "pending"

        t["project"] = project_pool[(i + seed) % len(project_pool)]
        tags = list({*(t.get("tags") or []), tag_pool[(i + seed) % len(tag_pool)]})
        tags = [x for x in tags if isinstance(x, str) and x.strip()]
        tags.sort()
        t["tags"] = tags

        desc = t.get("description")
        if not isinstance(desc, str) or not desc.strip():
            desc = "bench task"
        t["description"] = f"{desc} [L{i:05d}]"

        tasks.append(t)

    out["tasks"] = tasks
    out["indices"] = build_indices_v1(tasks)

    meta = out.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        out["meta"] = meta
    meta["fixture"] = {"name": "golden_payload_large_v1", "n_tasks": n_tasks, "seed": seed}

    return out
