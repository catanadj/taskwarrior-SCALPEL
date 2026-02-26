# SCALPEL Schema Evolution Protocol (Public Interface)

This document defines the **public contract** between:

Build/export pipeline (Taskwarrior → payload)  
and  
UI/render pipeline (payload → HTML/JS UI)

The payload schema is treated as an API. Changes must be deliberate, versioned, testable, and reversible.

---

## Scope

This protocol governs anything that affects the **payload contract**:

- `schema_version` and any versioned interpretation of payload fields
- The JSON embedded in HTML (e.g., `<script id="tw-data" type="application/json">...</script>`)
- Indices and normalization guarantees
- Public helper APIs (e.g., `scalpel.api`, `scalpel.validate`, `scalpel.html_extract`, query helpers)

Non-contract internals (private modules, internal helper functions) are not covered unless they change externally observable behavior.

---

## Definitions

**Schema**: The JSON payload contract emitted by build/export tools and consumed by render/UI.

**Latest schema**: The newest supported schema version `N` that all tools should emit by default.

**Legacy schema**: Any schema `< N` that is still accepted via upgrade/normalization.

**Normalization**: Converting any supported input payload into the canonical latest schema, with required indices and deterministic semantics.

**Validation**: Checking that a payload meets the required contract for a given schema version.

---

## Compatibility Policy

### Supported versions
- The library and tools MUST support:
  - the **latest** schema `N`
  - at least **one previous** schema `N-1` via upgrade
- Dropping support requires a deliberate change and explicit documentation.

### Backward compatibility rules (within a schema)
Within the same `schema_version`, changes must be **backward compatible** for consumers:
- Additive fields are OK (new optional keys).
- Tightening constraints is OK only if existing producers already satisfy them.
- Removing or renaming fields without an upgrade path is NOT OK.

### Schema version bump rules
Increment `schema_version` when:
- A required field is added
- A field changes type or meaning
- A structural change occurs (layout, indices contract, embedding contract)
- A default interpretation changes (semantic shift)

Do NOT bump `schema_version` for:
- new optional fields that do not change meaning
- internal-only changes (no payload surface impact)
- performance-only refactors with identical outputs

---

## Producer and Consumer Responsibilities

### Producers (smoke/build/export)
- MUST emit the latest schema version by default.
- MUST emit deterministic JSON for fixtures and contract tests.
- SHOULD keep embed format stable:
  - preferred: `<script id="tw-data" type="application/json">...</script>`
  - fallback formats should remain supported by extraction APIs if already public.

### Consumers (render/UI/tools)
- MUST accept latest schema directly.
- MUST accept supported legacy schemas via normalization/upgrade.
- MUST NOT require “build-time only” assumptions that cannot be validated at runtime.

---

## Determinism and Golden Fixtures

Golden fixtures are contract anchors and MUST be deterministic.

### Determinism requirements
- Timestamps like `generated_at` MUST be:
  - fixed during fixture generation, OR
  - excluded/normalized before comparison, OR
  - placed in a `meta` block that is explicitly ignored by fixture equivalence tests

### Canonical ordering requirements
- Tasks list ordering must be stable for fixtures (document the ordering rules).
- Index maps must be stable (key ordering doesn’t matter in JSON, but values must be deterministic).

---

## Required Building Blocks (Contract Surface)

A schema version is considered “supported” only if these are true:

1) **Schema definition exists**
- A canonical description of required keys and semantics.

2) **Upgrade path exists** (if legacy supported)
- `upgrade_payload(vK → vK+1)` style function(s) exist and are tested.

3) **Validator exists**
- Library validator returns human-readable issues.
- CLI tool validator exists (or is a thin wrapper over the library validator).

4) **Extraction exists** (if HTML embed is part of contract)
- Public function to extract JSON from HTML exists and is stable.

5) **Render exists**
- Payload can be rendered (replay) from JSON to HTML.

6) **Golden fixture exists**
- A canonical fixture for the latest schema exists under `tests/fixtures/`.

---

## Contract Test Requirements

Every schema bump MUST include (at minimum):

- `test_upgrade_prev_to_latest`  
  Given a legacy payload, normalization produces the latest schema.

- `test_validate_golden_fixture`  
  Golden latest fixture validates using:
  - library validation and tool validation (parity)

- `test_render_replay_invariants`  
  Rendered HTML contains the required embed block and invariant markers.

- `test_html_extract_roundtrip`  
  Extracting from:
  - smoke HTML
  - replay HTML  
  yields identical payloads after normalization (or exact match if expected).

- `test_fixture_is_up_to_date`  
  Regeneration produces identical output (determinism check).

---

## Change Procedure (Schema Workflows)

### A) Additive change (no schema bump)
1. Add optional field(s) to schema definition.
2. Ensure producers populate it (or leave empty safely).
3. Ensure consumers ignore it if unknown.
4. Add/extend contract tests.
5. Update golden fixture if field is emitted deterministically.

### B) Breaking/semantic change (schema bump)
1. Define new `schema_version = N+1` contract.
2. Implement `upgrade_payload_vN_to_vN1(payload)` (pure function).
3. Update `normalize_payload()` to call the upgrade chain.
4. Update producers to emit `N+1` by default.
5. Update validators to validate `N+1`.
6. Update render path to consume `N+1`.
7. Regenerate golden fixture for `N+1`.
8. Add/adjust contract tests.
9. Verify end-to-end parity: smoke HTML ↔ replay HTML extraction.

---

## Code Review Checklist (Must Pass)

When reviewing a payload/schema PR, confirm:

- [ ] Does the change alter the payload contract surface?
- [ ] If yes, is `schema_version` handling correct (bump or no bump)?
- [ ] Is there an upgrade path for legacy payloads (if required)?
- [ ] Do normalization + validation work on golden fixtures?
- [ ] Are golden fixtures deterministic (no time drift diffs)?
- [ ] Does HTML extraction remain stable (including fuzz/variants if present)?
- [ ] Are tool exit codes and error messages consistent and test-covered?
- [ ] Is `scalpel.api` public surface stable and explicitly exported?
- [ ] Are new fields documented (meaning, type, optional/required)?
- [ ] Did `./scripts/scalpel_test_contract.sh` pass cleanly?

---

## Practical Guardrails

- Prefer **additive, optional fields** over breaking changes.
- Prefer **upgrade/normalize** over branching behavior in render paths.
- Keep the public API **small, explicit, and locked** (via `__all__` / export list + contract tests).
- Treat fixtures as immutable unless a schema change justifies an update.

---

## Appendix: “Public Interface” Promise

The payload schema is the stable boundary between build/export and UI/render.

If a downstream consumer reads payload JSON and follows this protocol, they should:
- be able to upgrade and validate any supported payload
- render it via replay tooling
- extract embedded payload JSON from HTML
- query it using documented query helpers

Any deviation is a contract bug and should be caught by the contract suite.

