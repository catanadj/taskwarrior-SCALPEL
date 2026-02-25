# SCALPEL_QUERY_LANG_V3
from __future__ import annotations

import re
import shlex
from functools import lru_cache
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


class QueryError(ValueError):
    """Raised for invalid query expressions (parse or execution)."""


def _tasks_list(payload: Dict[str, Any]) -> List[Any]:
    tasks = payload.get("tasks") or []
    if not isinstance(tasks, list):
        return []
    return tasks


def _idx_map(payload: Dict[str, Any], key: str) -> Dict[str, Any]:
    idx = payload.get("indices") or {}
    if not isinstance(idx, dict):
        return {}
    m = idx.get(key)
    return m if isinstance(m, dict) else {}


def _as_int_set(v: Any) -> Set[int]:
    if not isinstance(v, list):
        return set()
    try:
        # Hot path: indices are produced by schema normalization as list[int].
        return set(v)
    except TypeError:
        s: Set[int] = set()
        for x in v:
            if isinstance(x, int):
                s.add(x)
        return s


def _intersect(cur: Optional[Set[int]], nxt: Set[int]) -> Set[int]:
    return nxt if cur is None else (cur & nxt)


def _task_desc(t: Dict[str, Any]) -> str:
    d = t.get("description")
    return d if isinstance(d, str) else ""


def _task_tags(t: Dict[str, Any]) -> Set[str]:
    tags = t.get("tags")
    if not isinstance(tags, list):
        return set()
    out: Set[str] = set()
    for x in tags:
        if isinstance(x, str) and x:
            out.add(x)
    return out


def _compile_regex_pat(pat: str) -> re.Pattern:
    try:
        return re.compile(pat)
    except re.error as e:
        raise QueryError(f"Invalid regex in query: {e}") from e


def _split_csv(s: str) -> List[str]:
    parts: List[str] = []
    for p in (s or "").split(","):
        p = p.strip()
        if p:
            parts.append(p)
    return parts


@dataclass(frozen=True)
class Query:
    projects: Tuple[str, ...] = ()
    statuses: Tuple[str, ...] = ()
    uuids: Tuple[str, ...] = ()
    days: Tuple[str, ...] = ()  # YYYY-MM-DD (optional; uses indices.by_day if present)

    tags_all: Tuple[str, ...] = ()
    tags_not: Tuple[str, ...] = ()

    # Regex filters on description (compiled at run-time)
    desc_re_all: Tuple[str, ...] = ()
    desc_re_not: Tuple[str, ...] = ()

    # Simple substring filters on description (case-insensitive)
    desc_sub_all: Tuple[str, ...] = ()

    @staticmethod
    @lru_cache(maxsize=256)
    def _cached_regex(pat: str) -> re.Pattern:
        return _compile_regex_pat(pat)

    @staticmethod
    def _strip_outer_quotes_raw(s: str) -> str:
        """Remove one layer of matching outer quotes without touching backslashes."""
        if not s or len(s) < 2:
            return s
        if (s[0] == s[-1]) and s[0] in ("'", '"'):
            return s[1:-1]
        return s

    @classmethod
    def parse(cls, expr: str) -> "Query":
        expr = (expr or "").strip()
        if not expr:
            return cls()

        try:
            toks = shlex.split(expr, posix=True)
        except ValueError as e:
            raise QueryError(f"Could not parse query (quoting/escaping error): {e}") from e

        projects: List[str] = []
        statuses: List[str] = []
        uuids: List[str] = []
        days: List[str] = []

        tags_all: List[str] = []
        tags_not: List[str] = []

        desc_re_all: List[str] = []
        desc_re_not: List[str] = []
        desc_sub_all: List[str] = []

        def add_csv(dst: List[str], raw: str) -> None:
            dst.extend(_split_csv(raw))

        for tok in toks:
            tok = tok.strip()
            if not tok:
                continue

            # UUID
            if tok.startswith("uuid:"):
                add_csv(uuids, tok[len("uuid:"):])
                continue
            if tok.startswith("uuid="):
                add_csv(uuids, tok[len("uuid="):])
                continue

            # project / status
            if tok.startswith("project:"):
                add_csv(projects, tok[len("project:"):])
                continue
            if tok.startswith("status:"):
                add_csv(statuses, tok[len("status:"):])
                continue

            # by_day (optional)
            if tok.startswith("day:"):
                add_csv(days, tok[len("day:"):])
                continue

            # tag include/exclude
            # Taskwarrior-style shorthand: +foo / -foo
            if tok.startswith("+") and len(tok) > 1:
                add_csv(tags_all, tok[1:])
                continue
            if tok.startswith("-") and len(tok) > 1:
                rest = tok[1:]
                # accept "-tag:blocked" too, but TW commonly uses "-blocked"
                if rest.startswith("tag:"):
                    rest = rest[len("tag:"):]
                add_csv(tags_not, rest)
                continue

            if tok.startswith("tag:"):
                add_csv(tags_all, tok[len("tag:"):])
                continue

            # Description regex include/exclude
            # Support: desc~PAT, description~PAT, desc!~PAT, description!~PAT
            if tok.startswith("desc!~") or tok.startswith("description!~"):
                prefix = "desc!~" if tok.startswith("desc!~") else "description!~"
                pat = tok[len(prefix):]
                pat = cls._strip_outer_quotes_raw(pat)
                if not pat:
                    raise QueryError(f"{prefix} requires a regex pattern")
                desc_re_not.append(pat)
                continue

            if tok.startswith("desc~") or tok.startswith("description~"):
                prefix = "desc~" if tok.startswith("desc~") else "description~"
                pat = tok[len(prefix):]
                pat = cls._strip_outer_quotes_raw(pat)
                if not pat:
                    raise QueryError(f"{prefix} requires a regex pattern")
                desc_re_all.append(pat)
                continue

            # Explicit substring form (optional): desc:foo / description:foo
            if tok.startswith("desc:") or tok.startswith("description:"):
                prefix = "desc:" if tok.startswith("desc:") else "description:"
                sub = tok[len(prefix):]
                sub = cls._strip_outer_quotes_raw(sub)
                if sub:
                    desc_sub_all.append(sub)
                continue

            # Bare token => substring include on description (case-insensitive)
            desc_sub_all.append(tok)

        return cls(
            projects=tuple(projects),
            statuses=tuple(statuses),
            uuids=tuple(uuids),
            days=tuple(days),
            tags_all=tuple(tags_all),
            tags_not=tuple(tags_not),
            desc_re_all=tuple(desc_re_all),
            desc_re_not=tuple(desc_re_not),
            desc_sub_all=tuple(desc_sub_all),
        )

    def run_indices(self, payload: Dict[str, Any]) -> Set[int]:
        tasks = _tasks_list(payload)
        n_tasks = len(tasks)

        by_uuid = _idx_map(payload, "by_uuid")
        by_status = _idx_map(payload, "by_status")
        by_project = _idx_map(payload, "by_project")
        by_tag = _idx_map(payload, "by_tag")
        by_day = _idx_map(payload, "by_day")

        cur: Optional[Set[int]] = None

        # uuids (OR over uuids, then AND with others)
        if self.uuids:
            s: Set[int] = set()
            for u in self.uuids:
                if not isinstance(u, str) or not u:
                    continue
                idx = by_uuid.get(u)
                if isinstance(idx, int):
                    s.add(idx)
            cur = _intersect(cur, s)

        # statuses (OR within group)
        if self.statuses:
            s: Set[int] = set()
            for st in self.statuses:
                s |= _as_int_set(by_status.get(st))
            cur = _intersect(cur, s)

        # projects (OR within group)
        if self.projects:
            s: Set[int] = set()
            for pr in self.projects:
                s |= _as_int_set(by_project.get(pr))
            cur = _intersect(cur, s)

        # days (OR within group)
        if self.days:
            s: Set[int] = set()
            for d in self.days:
                s |= _as_int_set(by_day.get(d))
            cur = _intersect(cur, s)

        # tags_all => AND across required tags
        for tag in self.tags_all:
            s = _as_int_set(by_tag.get(tag))
            cur = _intersect(cur, s)

        # If no indexed constraints were provided, start with all tasks
        if cur is None:
            cur = set(range(n_tasks))

        # tags_not => subtract
        if self.tags_not:
            deny: Set[int] = set()
            for tag in self.tags_not:
                deny |= _as_int_set(by_tag.get(tag))
            cur -= deny

        # Substring filters on description
        if self.desc_sub_all:
            needles = [x.lower() for x in self.desc_sub_all if isinstance(x, str) and x]
            if needles:
                kept: Set[int] = set()
                for i in cur:
                    if i < 0 or i >= n_tasks:
                        continue
                    t = tasks[i]
                    d = _task_desc(t) if isinstance(t, dict) else ""
                    d = d.lower()
                    ok = True
                    for n in needles:
                        if n not in d:
                            ok = False
                            break
                    if ok:
                        kept.add(i)
                cur = kept

        # Regex filters on description
        if self.desc_re_all or self.desc_re_not:
            re_all = [self._cached_regex(p) for p in self.desc_re_all]
            re_not = [self._cached_regex(p) for p in self.desc_re_not]

            kept: Set[int] = set()
            for i in cur:
                if i < 0 or i >= n_tasks:
                    continue
                t = tasks[i]
                d = _task_desc(t) if isinstance(t, dict) else ""
                ok = True
                for r in re_all:
                    if not r.search(d):
                        ok = False
                        break
                if not ok:
                    continue
                for r in re_not:
                    if r.search(d):
                        ok = False
                        break
                if ok:
                    kept.add(i)
            cur = kept

        return cur

    def run(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        tasks = _tasks_list(payload)
        n_tasks = len(tasks)
        idxs = self.run_indices(payload)
        if not idxs:
            return []

        out: List[Dict[str, Any]] = []
        # Preserve original task order without scanning all tasks for sparse hits.
        ordered = sorted(i for i in idxs if 0 <= i < n_tasks)
        for i in ordered:
            t = tasks[i]
            if isinstance(t, dict):
                out.append(t)
        return out


def compile_query(expr: str) -> Query:
    return Query.parse(expr)
