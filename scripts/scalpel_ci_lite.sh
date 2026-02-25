#!/usr/bin/env bash
set -euo pipefail

# scalpel_ci_lite.sh
# Runs: clean -> doctor -> smoke(strict) -> check
#
# Usage:
#   ./scripts/scalpel_ci_lite.sh
#   ./scripts/scalpel_ci_lite.sh --out build/scalpel_smoke.html
#   ./scripts/scalpel_ci_lite.sh --allow-dirty
#   ./scripts/scalpel_ci_lite.sh -- --days 14 --pretty   (args after `--` are forwarded to smoke step)

usage() {
  cat <<'EOF'
scalpel_ci_lite.sh - CI-lite runner for SCALPEL

Steps:
  1) clean
  2) doctor
  3) smoke (strict)
  4) check

Options:
  --out PATH         Output HTML path (default: build/scalpel_ci_smoke.html)
  --allow-dirty      Do not fail if git working tree is dirty before/after
  --no-clean         Skip clean step
  --no-doctor        Skip doctor step
  --no-smoke         Skip smoke step
  --no-check         Skip check step
  --clean-logs      Remove existing step logs in build/ci-lite before running
  --print-logs      Print step log paths at end (also on failure)
  --max-ms STEP=MS    Warn if STEP exceeds MS (repeatable)
  --perf-strict       Fail if any step exceeds its --max-ms budget

  --selftest-fail STEP  Force a failure in the named step (for testing log/tail UX)
  -h, --help         Show this help

Pass-through:
  All args after `--` are forwarded to the smoke step.
EOF
}

die() { echo "[ci-lite] ERROR: $*" >&2; exit 2; }


_now_ns() {
  # best-effort time source; used for step durations
  local v
  v="$(date +%s%N 2>/dev/null || true)"
  if [[ -n "$v" ]]; then
    echo "$v"
    return 0
  fi
  python3 - <<'PY'
import time
print(time.time_ns())
PY
}

repo_root="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1
  pwd
)"
# --- failure shrink (auto-generated) ---
ci_lite_failure_shrink() {
  # Best-effort: never fail CI due to shrink itself.
  local step="${1:-unknown}"
  if [[ "${SCALPEL_CI_NO_SHRINK:-0}" == "1" ]]; then
    return 0
  fi

  mkdir -p "$FAIL_DIR" || true

  # Preserve the primary artifacts if present.
  if [[ -f "$JSON_OUT" ]]; then
    cp -f "$JSON_OUT" "$FAIL_JSON" || true
  fi
  if [[ -f "$OUT" ]]; then
    cp -f "$OUT" "$FAIL_HTML" || true
  fi

  # Write reproducibility notes.
  {
    echo "scalpel CI-lite failure shrink"
    echo "step: $step"
    echo "repo_root: $repo_root"
    echo "log_dir: $LOG_DIR"
    echo "fail_dir: $FAIL_DIR"
    echo
    if [[ -f "$FAIL_JSON" ]]; then
      echo "Repro (validate payload):"
      echo "  PYTHONPATH=\"$repo_root\" ${PY:-python3} -m scalpel.tools.validate_payload --in \"$FAIL_JSON\""
      echo
      echo "Repro (render replay from payload):"
      echo "  PYTHONPATH=\"$repo_root\" ${PY:-python3} -m scalpel.tools.render_payload --in \"$FAIL_JSON\" --out \"${FAIL_DIR}/replay.html\""
      echo
      echo "Minify examples:"
      echo "  PYTHONPATH=\"$repo_root\" ${PY:-python3} -m scalpel.tools.minify_fixture --in \"$FAIL_JSON\" --q \"status:pending\" --out \"${FAIL_DIR}/min_pending.json\" --pretty"
      echo "  PYTHONPATH=\"$repo_root\" ${PY:-python3} -m scalpel.tools.minify_fixture --in \"$FAIL_JSON\" --q \"uuid:<UUID>\" --out \"${FAIL_DIR}/min_uuid_1.json\" --pretty"
    else
      echo "No payload JSON found at JSON_OUT=$JSON_OUT"
    fi
  } > "${FAIL_DIR}/README.txt" 2>/dev/null || true
  if [[ ! -f "$FAIL_JSON" ]]; then
    # Ensure at least one min_*.json exists even when the failing step happens before payload.json.
    mkdir -p "$FAIL_DIR" || true
    printf '{"schema_version":2,"cfg":{},"tasks":[],"indices":{},"meta":{}}
' > "${FAIL_DIR}/min_stub.json" 2>/dev/null || true
    return 0
  fi
  # Helper to minify with a query (best-effort).
  _ci_try_minify() {
    local q="$1"
    local outp="$2"
    PYTHONPATH="$repo_root" "${PY:-python3}" -m scalpel.tools.minify_fixture \
      --in "$FAIL_JSON" \
      --q "$q" \
      --out "$outp" \
      --pretty \
      >/dev/null 2>&1 || true

    # Contract + UX: ensure at least one min_*.json artifact exists even if minify fails.
    if [[ ! -s "$outp" ]]; then
      # Fallback: keep cfg/meta, keep first task, rebuild indices via upgrade_payload if possible.
      "${PY:-python3}" - "$FAIL_JSON" "$outp" "$repo_root" >/dev/null 2>&1 <<'PY'
import json, sys
from pathlib import Path

in_path, out_path, repo_root = sys.argv[1:4]

try:
    obj = json.load(open(in_path, "r", encoding="utf-8"))
except Exception:
    obj = {}

cfg = obj.get("cfg") if isinstance(obj.get("cfg"), dict) else {}
meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
tasks_raw = obj.get("tasks") if isinstance(obj.get("tasks"), list) else []
tasks = [t for t in tasks_raw if isinstance(t, dict)][:1]

payload = {"cfg": cfg, "tasks": tasks, "meta": meta}

try:
    sys.path.insert(0, repo_root)
    from scalpel.schema import upgrade_payload, LATEST_SCHEMA_VERSION
    payload = upgrade_payload(payload, target_version=int(LATEST_SCHEMA_VERSION))
except Exception:
    payload.setdefault("schema_version", obj.get("schema_version", 2))
    payload.setdefault("indices", {})

Path(out_path).parent.mkdir(parents=True, exist_ok=True)
Path(out_path).write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
    fi
  }

  # A couple of broad slices:
  _ci_try_minify "status:pending"   "${FAIL_DIR}/min_pending.json"
  _ci_try_minify "status:completed" "${FAIL_DIR}/min_completed.json"

  # UUID slices: first few tasks from the failing payload.
  local uuids
  uuids="$("${PY:-python3}" - <<'PY' "$FAIL_JSON" 2>/dev/null || true
import json, sys
p = sys.argv[1]
try:
    obj = json.load(open(p, "r", encoding="utf-8"))
except Exception:
    sys.exit(0)
tasks = obj.get("tasks") or []
n = 0
for t in tasks:
    if not isinstance(t, dict):
        continue
    u = t.get("uuid")
    if isinstance(u, str) and u.strip():
        print(u.strip())
        n += 1
    if n >= 5:
        break
PY
)"
  local i=0
  while IFS= read -r u; do
    [[ -z "$u" ]] && continue
    i=$((i+1))
    _ci_try_minify "uuid:${u}" "${FAIL_DIR}/min_uuid_${i}.json"
  done <<< "$uuids"
  # ddmin shrink (optional)
  # - automatic when the failing step is validate(payload)
  # - or manually force via: SCALPEL_CI_DDMIN_CMD='... {in} ...'
  local ddmin_cmd=""
  if [[ -n "${SCALPEL_CI_DDMIN_CMD:-}" ]]; then
    ddmin_cmd="${SCALPEL_CI_DDMIN_CMD}"
  elif [[ "$step" == "validate(payload)" ]]; then
    ddmin_cmd="PYTHONPATH='${repo_root}' ${PY:-python3} -m scalpel.tools.validate_payload --in {in}"
  fi

  if [[ -n "$ddmin_cmd" ]]; then
    PYTHONPATH="$repo_root" "${PY:-python3}" -m scalpel.tools.ddmin_shrink \
      --in "$FAIL_JSON" \
      --out "$FAIL_DDMIN_JSON" \
      --cmd "$ddmin_cmd" \
      --timeout "${SCALPEL_CI_DDMIN_TIMEOUT:-20}" \
      --max-tests "${SCALPEL_CI_DDMIN_MAX_TESTS:-200}" \
      --pretty \
      >/dev/null 2>&1 || true
  fi


  return 0
}
# --- /failure shrink ---


cd "$repo_root"
OUT="build/scalpel_ci_smoke.html"
LOG_DIR="build/ci-lite"
LOG_DIR="${SCALPEL_CI_LOG_DIR:-$LOG_DIR}"
JSON_OUT="${LOG_DIR}/payload.json"
FAIL_DIR="${LOG_DIR}/fail"
FAIL_JSON="${FAIL_DIR}/payload.json"
FAIL_DDMIN_JSON="${FAIL_DIR}/ddmin.json"
FAIL_HTML="${FAIL_DIR}/smoke.html"
SUMMARY="$LOG_DIR/summary.tsv"
TAIL_LINES="${SCALPEL_CI_TAIL_LINES:-120}"
mkdir -p "$LOG_DIR"
LOG_FILES=()

ALLOW_DIRTY=0
NO_CLEAN=0
NO_DOCTOR=0
NO_SMOKE=0
NO_CHECK=0
CLEAN_LOGS=0
PERF_STRICT=0
MAX_MS_RULES=()

PRINT_LOGS=0
SELFTEST_FAIL=""
SMOKE_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      [[ $# -ge 2 ]] || die "--out requires a value"
      OUT="$2"
      shift 2
      ;;
    --allow-dirty)
      ALLOW_DIRTY=1
      shift
      ;;
    --no-clean)  NO_CLEAN=1; shift ;;
    --no-doctor) NO_DOCTOR=1; shift ;;
    --no-smoke)  NO_SMOKE=1; shift ;;
    --no-check)  NO_CHECK=1; shift ;;
    --clean-logs)
      CLEAN_LOGS=1
      shift
      ;;

    --print-logs)
      PRINT_LOGS=1
      shift
      ;;

    --selftest-fail)
      [[ $# -ge 2 ]] || die "--selftest-fail requires a step name (clean|doctor|smoke|check)"
      SELFTEST_FAIL="$2"
      shift 2
      ;;

    --max-ms)

      [[ $# -ge 2 ]] || die "--max-ms requires STEP=MS"

      MAX_MS_RULES+=("$2")

      shift 2

      ;;

    --perf-strict)

      PERF_STRICT=1

      shift

      ;;


    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      SMOKE_ARGS+=("$@")
      break
      ;;
    *)
      die "Unknown argument: $1 (use --help)"
      ;;
  esac
done


# Optional env: SCALPEL_CI_MAX_MS="doctor=1500,smoke(strict)=5000"
if [[ -n "${SCALPEL_CI_MAX_MS:-}" ]]; then
  IFS=',' read -r -a _scalpel_ci_env_rules <<< "${SCALPEL_CI_MAX_MS}"
  for _r in "${_scalpel_ci_env_rules[@]}"; do
    [[ -n "${_r}" ]] && MAX_MS_RULES+=("${_r}")
  done
fi

# Validate selftest step name (optional)
if [[ -n "${SELFTEST_FAIL:-}" ]]; then
  case "$SELFTEST_FAIL" in
    clean|doctor|check|smoke|smoke*) ;;  # smoke* covers smoke(strict)
    *) die "--selftest-fail must be one of: clean|doctor|smoke|check" ;;
  esac
fi

mkdir -p "$LOG_DIR"



# Optional: clear previous step logs (requires --clean-logs)
if [[ "${CLEAN_LOGS:-0}" -eq 1 ]]; then
  rm -f "$LOG_DIR"/*.log 2>/dev/null || true
  rm -f "$SUMMARY" 2>/dev/null || true
fi

require_git_clean() {
  if ! command -v git >/dev/null 2>&1; then
    return 0
  fi
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi
  local s
  s="$(git status --porcelain)"
  if [[ -n "$s" ]]; then
    echo "$s" >&2
    die "Git working tree is dirty (use --allow-dirty to bypass)"
  fi
}



# step counter used for stable log ordering
STEP_N=0

_log_path() {
  # $1 step name
  local step="$1"
  # sanitize
  step="${step//[^a-zA-Z0-9._-]/_}"
  echo "${LOG_DIR}/$(printf "%02d" "${STEP_N}")_${step}.log"
}


_selftest_match() {
  local name="$1"
  local want="${SELFTEST_FAIL:-}"
  [[ -z "$want" ]] && return 1
  [[ "$want" == "$name" ]] && return 0
  # allow `--selftest-fail smoke` to match smoke(strict)
  if [[ "$want" == "smoke" && "$name" == smoke* ]]; then
    return 0
  fi
  # allow smoke* patterns
  if [[ "$want" == smoke* && "$name" == smoke* ]]; then
    return 0
  fi
  return 1
}

# Perf budget checking (warn-only by default; fail with --perf-strict)
declare -A _SCALPEL_MAX_MS=()

_perf_add_rule() {
  local rule="$1"
  local step="${rule%%=*}"
  local ms="${rule#*=}"
  [[ -n "$step" && -n "$ms" ]] || return 0
  [[ "$ms" =~ ^[0-9]+$ ]] || return 0
  _SCALPEL_MAX_MS["$step"]="$ms"
}

_perf_load_rules() {
  _SCALPEL_MAX_MS=()
  local r
  for r in "${MAX_MS_RULES[@]}"; do
    _perf_add_rule "$r"
  done
}

_check_perf_budgets() {
  _perf_load_rules
  if [[ "${#_SCALPEL_MAX_MS[@]}" -eq 0 ]]; then
    return 0
  fi
  if [[ ! -f "${SUMMARY:-}" ]]; then
    return 0
  fi

  local violations=0
  local step rc ms log
  while IFS=$'\t' read -r step rc ms log; do
    [[ -z "$step" ]] && continue
    [[ "$step" == "step" ]] && continue
    if [[ -n "${_SCALPEL_MAX_MS[$step]:-}" ]]; then
      local budget="${_SCALPEL_MAX_MS[$step]}"
      if [[ "$ms" =~ ^[0-9]+$ ]] && (( ms > budget )); then
        violations=$((violations + 1))
        echo "[ci-lite] PERF WARN: step '$step' took ${ms}ms > budget ${budget}ms (log: ${log})" >&2
      fi
    fi
  done < "${SUMMARY}"

  if (( violations > 0 )) && [[ "${PERF_STRICT:-0}" -eq 1 ]]; then
    echo "[ci-lite] PERF STRICT: failing due to ${violations} budget violation(s)." >&2
    return 3
  fi
  return 0
}


run_step() {
  local name="$1"; shift
  local logfile

  logfile="$(_log_path "$name")"


  LOG_FILES+=("$logfile")
  echo
  echo "[ci-lite] === $name ==="
  echo "[ci-lite] log: $logfile"
{
  echo "[ci-lite] ts: $(date -Is)"
  echo "[ci-lite] step: $name"
  printf '[ci-lite] cmd:'; printf ' %q' "$@"; echo
  echo "[ci-lite] env: SCALPEL_SKIP_DOCTOR=${SCALPEL_SKIP_DOCTOR:-} SCALPEL_SKIP_SMOKE=${SCALPEL_SKIP_SMOKE:-} PYTHON=${PYTHON:-}"
  echo
} >"$logfile"
  local t0_ns="$(_now_ns)"
  set +e
  local cmd=("$@")
  if _selftest_match "$name"; then
    cmd=(bash -lc "echo '[ci-lite] selftest: forced failure for step: '"\"$name\"" >&2; exit 99")
  fi

  "${cmd[@]}" 2>&1 | tee -a "$logfile"
  local rc="${PIPESTATUS[0]}"
  local t1_ns="$(_now_ns)"
  local elapsed_ms=0
  if [[ -n "${t0_ns:-}" && -n "${t1_ns:-}" ]]; then
    elapsed_ms=$(( (t1_ns - t0_ns) / 1000000 ))
  fi

  # write/update summary.tsv (step\trc\tms\tlog)
  if [[ ! -f "$SUMMARY" ]]; then
    printf "step\trc\tms\tlog\n" >"$SUMMARY"
  fi
  printf "%s\t%s\t%s\t%s\n" "$name" "$rc" "$elapsed_ms" "$logfile" >>"$SUMMARY"

  set -e

  if [[ "$rc" -ne 0 ]]; then
    echo >&2
    echo "[ci-lite] FAILED step: $name (exit $rc)" >&2
    ci_lite_failure_shrink "${name:-${label:-unknown}}" || true
    echo "[ci-lite] log: $logfile" >&2
    echo "[ci-lite] --- tail (${TAIL_LINES} lines) ---" >&2
    tail -n "$TAIL_LINES" "$logfile" >&2 || true
    echo "[ci-lite] --- /tail ---" >&2
    exit "$rc"
  fi
}

print_logs() {
  # If no step logs were produced (e.g. all steps skipped), do not print anything.
  if [[ "${#LOG_FILES[@]}" -eq 0 ]]; then
    return 0
  fi

  echo
  echo "[ci-lite] === logs ==="
  local out_path="${OUT:-}"
  local out_status="missing"
  if [[ -n "$out_path" && -e "$out_path" ]]; then
    out_status="exists"
  fi
  echo "[ci-lite] out: $out_path ($out_status)"
  local dir_path="${LOG_DIR:-}"
  local dir_status="missing"
  if [[ -n "$dir_path" && -d "$dir_path" ]]; then
    dir_status="exists"
  fi
  echo "[ci-lite] dir: $dir_path ($dir_status)"
  local f
  for f in "${LOG_FILES[@]}"; do
    local st="missing"
    [[ -e "$f" ]] && st="exists"
    echo "[ci-lite] log: $f ($st)"
  done
}

trap 'if [[ "${PRINT_LOGS:-0}" -eq 1 ]]; then print_logs; fi' EXIT

# Dirty-check before
if [[ "$ALLOW_DIRTY" -eq 0 ]]; then
  require_git_clean
fi

mkdir -p "$(dirname "$OUT")"

# 1) clean
if [[ "$NO_CLEAN" -eq 0 ]]; then
  STEP_N=$((STEP_N+1))
  if [[ -x "$repo_root/scripts/scalpel_clean.sh" ]]; then
    run_step "clean" "$repo_root/scripts/scalpel_clean.sh"
  elif command -v scalpel-clean >/dev/null 2>&1; then
    run_step "clean" scalpel-clean
  else
    run_step "clean" bash -lc "rm -f \"${OUT}\""
  fi
fi

# 2) doctor
if [[ "$NO_DOCTOR" -eq 0 ]]; then
  STEP_N=$((STEP_N+1))
  if [[ -x "$repo_root/scripts/scalpel_doctor.sh" ]]; then
    run_step "doctor" "$repo_root/scripts/scalpel_doctor.sh"
  elif command -v scalpel-doctor >/dev/null 2>&1; then
    run_step "doctor" scalpel-doctor
  else
    die "No doctor runner found (expected ./scripts/scalpel_doctor.sh or scalpel-doctor on PATH)"
  fi
fi

# 3) smoke (strict)
if [[ "$NO_SMOKE" -eq 0 ]]; then
  STEP_N=$((STEP_N+1))
  if [[ -x "$repo_root/scripts/scalpel_smoke_strict.sh" ]]; then
    run_step "smoke(strict)" env SCALPEL_SKIP_DOCTOR=1 SCALPEL_SMOKE_OUT_JSON="$JSON_OUT" "$repo_root/scripts/scalpel_smoke_strict.sh" "$OUT" "${SMOKE_ARGS[@]}"
  elif command -v scalpel-smoke-build >/dev/null 2>&1; then
    run_step "smoke(strict)" scalpel-smoke-build --out "$OUT" --strict "${SMOKE_ARGS[@]}"
  else
    die "No smoke runner found (expected ./scripts/scalpel_smoke_strict.sh or scalpel-smoke-build on PATH)"
  fi
fi

# 3.5) validate payload (schema v1) - both HTML extraction and raw JSON
# Runs after smoke(strict). If smoke was skipped, runs only if OUT exists.
if [[ "${NO_SMOKE:-0}" -eq 0 ]]; then
  if [[ -n "${STEP_N:-}" ]]; then
    STEP_N=$((STEP_N+1))
  fi

  if [[ -x "$repo_root/scripts/scalpel_validate_payload.sh" ]]; then
    run_step "validate(payload)" "$repo_root/scripts/scalpel_validate_payload.sh" --from-html "$OUT" --in "$JSON_OUT"
  else
    run_step "validate(payload)" bash -lc "PYTHONPATH='${repo_root}' ${PYTHON:-python3} -m scalpel.tools.validate_payload --from-html '$OUT' --in '$JSON_OUT'"
  fi
fi

# 3.6) selftest: force failure after smoke/validate (useful for shrink contracts)
if [[ "${SCALPEL_CI_FAIL_AFTER_SMOKE:-0}" == "1" ]]; then
  if [[ -n "${STEP_N:-}" ]]; then
    STEP_N=$((STEP_N+1))
  fi
  run_step "selftest(fail-after-smoke)" bash -lc "exit 1"
fi



# 4) check
if [[ "$NO_CHECK" -eq 0 ]]; then
  STEP_N=$((STEP_N+1))
  if [[ -x "$repo_root/scripts/scalpel_check_strict.sh" ]]; then
    run_step "check" env SCALPEL_SKIP_DOCTOR=1 SCALPEL_SKIP_SMOKE=1 "$repo_root/scripts/scalpel_check_strict.sh" --out "$OUT" --skip-doctor --skip-smoke
  elif command -v scalpel-check >/dev/null 2>&1; then
    run_step "check" scalpel-check --out "$OUT"
  else
    die "No check runner found (expected ./scripts/scalpel_check_strict.sh or scalpel-check on PATH)"
  fi
fi

# Dirty-check after (ensures tooling doesn't mutate tracked files)
if [[ "$ALLOW_DIRTY" -eq 0 ]]; then
  require_git_clean
fi

echo

# Perf budgets (warn-only unless --perf-strict)
_perf_rc=0
_check_perf_budgets || _perf_rc=$?
if [[ "${_perf_rc}" -ne 0 ]]; then
  exit "${_perf_rc}"
fi

echo "[ci-lite] OK: $OUT"

echo "[ci-lite] logs: $LOG_DIR"

echo "[ci-lite] summary: $SUMMARY"