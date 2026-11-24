# CONSTRUCTOR-DEAD-PARAM

> **Detector class**: `CONSTRUCTOR_DEAD_PARAM`
> **Inject into**: Lens A (Access/State)
> **Category**: Initialization
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-61
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Constructor accepts parameter(s) that are never used in initialization logic.
This creates misleading API surface and can hide misconfiguration or abandoned controls.

## Vulnerable pattern

- constructor signature includes parameter
- parameter is not referenced in constructor body
- consumers assume parameter affects contract behavior

## Secure pattern

- remove unused constructor parameters
- or consume them in explicit validated initialization flow

## Detection

- parse constructor parameter list
- detect parameter identifiers with zero references in constructor body

## False-positive caveats (Gate C / FP-10 evidence)

- macro-generated code may consume parameters indirectly
- reference could exist only in conditional compile paths

## Minimum tests (PoC and regression targets)

- constructor ABI matches actual required initialization fields
- deployment rejects stale/outdated constructor argument formats
