# NO-ACCESS-CONTROL-MUTATION

> **Detector class**: `NO_ACCESS_CONTROL_MUTATION`
> **Inject into**: Lens A (Access/State)
> **Category**: Access control
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-6, AV-8, AV-90
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Privileged or configuration mutation functions are callable without explicit access control.
Unrestricted callers can alter protocol configuration or governance-critical state.

## Vulnerable pattern

- external/public mutation function (`set_*`, `register_*`, `upgrade`, `pause`, etc.)
- writes privileged storage or role mappings
- no owner/role/caller check

## Secure pattern

- gate privileged mutations with explicit owner/role checks
- centralize authorization paths and test denied callers

## Detection

- risky mutation function names with storage writes/role mutation
- missing explicit access control markers in function path

## False-positive caveats (Gate C / FP-10 evidence)

- intentionally permissionless product features (must be documented)
- access control enforced by surrounding ABI/router layer

## Minimum tests (PoC and regression targets)

- unauthorized caller reverts on mutation function
- authorized caller succeeds and state transitions are correct
