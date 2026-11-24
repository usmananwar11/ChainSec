# UNPROTECTED-INITIALIZER

> **Detector class**: `UNPROTECTED_INITIALIZER`
> **Inject into**: Lens A (Access/State)
> **Category**: Initialization
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-16
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Initializer function remains externally callable without caller authorization, enabling front-run or hostile initialization.

## Vulnerable pattern

- public `initialize` outside constructor-only path
- only guard is `is_zero()` one-time check
- initializer writes privileged contract addresses/roles

## Secure pattern

- constructor-only initialization, or
- protected initializer restricted to deployer/factory/governance

## Detection

- publicly reachable `initialize` with storage writes
- no access control assertions in initializer body

## False-positive caveats (Gate C / FP-10 evidence)

- initializer callable only in factory-controlled deployment transaction pattern with proven atomicity

## Minimum tests (PoC and regression targets)

- unauthorized initializer call reverts
- repeated initialization reverts
