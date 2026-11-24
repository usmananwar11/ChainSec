# SILENT-NO-OP

> **Detector class**: `SILENT_NO_OP`
> **Inject into**: Lens D (Edge cases/Math)
> **Category**: State updates
> **Related attack vectors** (heuristics.md, Extended heuristics): none
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

A branch intended to update state performs no action, silently skipping required updates.

## Vulnerable pattern

- `match/if` branch returns unit `()` or empty branch on existing-key path
- expected update call is absent for non-empty branch

## Secure pattern

- update existing entries explicitly
- emit event or return status when no-op is intentional

## Detection

- branch matching `Option::Some` (or equivalent) with empty action in state update function

## False-positive caveats (Gate C / FP-10 evidence)

- explicit idempotent behavior with complete test coverage and documentation

## Minimum tests (PoC and regression targets)

- existing-item update test changes state
- idempotence behavior test if intentionally no-op
- intentional no-op path emits explicit status/event signal
