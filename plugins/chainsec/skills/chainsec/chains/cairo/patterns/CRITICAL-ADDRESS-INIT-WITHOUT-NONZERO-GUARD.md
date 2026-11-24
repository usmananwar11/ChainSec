# CRITICAL-ADDRESS-INIT-WITHOUT-NONZERO-GUARD

> **Detector class**: `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD`
> **Inject into**: Lens A (Access/State)
> **Category**: Initialization
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-3, AV-88
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Constructor stores privileged/critical `ContractAddress` parameters without non-zero validation.

## Vulnerable pattern

- constructor receives addresses like `admin`, `owner`, `registry`, `vault`, `oracle`
- writes them to storage / role setup directly
- no `is_non_zero` assertion

## Secure pattern

- validate each critical constructor address with non-zero checks before storing

## Detection

- constructor includes critical `ContractAddress` params
- params used in `write(...)` / `initializer(...)` / `_grant_role(...)`
- missing nearby non-zero assertions

## False-positive caveats (Gate C / FP-10 evidence)

- some protocols intentionally allow zero sentinel values
- if intentional, must be explicitly documented and tested

## Minimum tests (PoC and regression targets)

- constructor reverts when any critical address is zero
- constructor succeeds with valid addresses and persists expected state
