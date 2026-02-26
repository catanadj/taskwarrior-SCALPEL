# Production Readiness Checklist

Last updated: 2026-02-18

## Correctness and Reliability

- [x] Handle malformed compact Taskwarrior timestamps without crashing (`scalpel/taskwarrior.py`).
- [x] Align schema normalization and validation contracts for `meta` presence (`scalpel/schema_v1.py`, `scalpel/validate.py`).
- [x] Align `cfg.px_per_min` type expectations between runtime and schema validators (`scalpel/payload.py`, `scalpel/schema_contracts/v1.py`, `scalpel/schema_contracts/v2.py`).
- [x] Ensure nautical hook loading failures degrade gracefully instead of aborting payload generation (`scalpel/payload.py`).

## Security

- [x] Shell-quote generated Taskwarrior modify commands to prevent command injection when copied to a shell (`scalpel/planner.py`).

## Tests

- [x] Add coverage for malformed compact timestamp parsing behavior.
- [x] Add coverage ensuring generated payloads from `build_payload()` pass public validation.
- [x] Add coverage for shell-escaping behavior in generated planner commands.
- [x] Add coverage for broken `nautical_core` module load behavior.

## Observability

- [x] Add explicit warnings/log markers for timestamp parse failures.
- [x] Add explicit warnings/log markers for nautical hook load failures.
