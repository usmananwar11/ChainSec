# UNEXPECTED-ACCESS-CONTROL

> **Detector class**: `UNEXPECTED_ACCESS_CONTROL`
> **Inject into**: Lens A (Access/State)
> **Category**: Access control
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-9
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

A privileged action is callable by an unexpected actor class, creating governance or economic behavior divergence.

## Vulnerable pattern

- authorization check permits extra caller path (`sender || recipient`, etc.)
- operation mutates lifecycle-critical state (cancel, settle, upgrade, withdraw)

## Secure pattern

- enforce actor set from protocol specification
- separate user actions from privileged lifecycle operations

## Detection

- OR-combined authorization for sensitive function
- secondary actor path not aligned with documented role intent

## False-positive caveats (Gate C / FP-10 evidence)

- protocol intentionally supports multi-party cancellation and documents it clearly

## Minimum tests (PoC and regression targets)

- actor matrix tests for sensitive functions
- regression test for spec-aligned authorization rules
