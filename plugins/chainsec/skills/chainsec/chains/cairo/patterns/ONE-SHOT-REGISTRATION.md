# ONE-SHOT-REGISTRATION

> **Detector class**: `ONE_SHOT_REGISTRATION`
> **Inject into**: Lens A (Access/State)
> **Category**: Access control / dependencies
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-5, AV-66
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Critical dependency registration is enforced as write-once without a safe operator
recovery/update path. A wrong first registration can permanently brick integrations.

## Vulnerable pattern

- `register_*` function writes critical address with one-shot guard
- no `set_*`/`update_*`/recovery function for the same field
- downstream logic assumes registration is always valid

## Secure pattern

- keep initial registration guard
- add owner/governance-controlled recovery setter with explicit constraints
- require event emission and operational runbook for updates

## Detection

- detect one-shot guard around `self.<field>.read()`
- check writers for that field are limited to constructor/initializer + register function

## False-positive caveats (Gate C / FP-10 evidence)

- explicitly immutable architecture with documented migration strategy
- intentionally non-upgradeable minimal contracts with no external dependencies

## Minimum tests (PoC and regression targets)

- first registration or initialization succeeds
- duplicate registration reverts
- initializer-first deployment path preserves recovery semantics
- authorized recovery/update path works when enabled
- unauthorized recovery/update attempts revert
