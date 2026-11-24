# UPGRADE-CLASS-HASH-WITHOUT-NONZERO-GUARD

> **Detector class**: `UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD`
> **Inject into**: Lens A (Access/State)
> **Category**: Upgrades
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-2
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Upgrade path accepts `new_class_hash` without explicit non-zero validation.

## Vulnerable pattern

- upgrade function forwards `new_class_hash` directly to class replacement
- no `is_non_zero` / equivalent assertion on `new_class_hash`

## Secure pattern

- `assert(new_class_hash.is_non_zero(), '...')` before upgrade call

## Detection

- function `upgrade(... new_class_hash ...)` present
- calls `replace_class_syscall` or `upgradeable.upgrade`
- missing non-zero guard around `new_class_hash`

## False-positive caveats (Gate C / FP-10 evidence)

- some upgrade libraries may reject zero hash internally
- explicit guard still recommended for clearer invariant and error surface

## Minimum tests (PoC and regression targets)

- upgrade with zero class hash reverts
- upgrade with valid class hash succeeds under authorized caller
