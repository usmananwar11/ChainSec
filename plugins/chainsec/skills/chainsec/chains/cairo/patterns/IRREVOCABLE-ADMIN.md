# IRREVOCABLE-ADMIN

> **Detector class**: `IRREVOCABLE_ADMIN`
> **Inject into**: Lens A (Access/State)
> **Category**: Access control
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-4, AV-18
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

A privileged admin/owner is initialized but there is no explicit rotation, transfer,
or revocation path. Compromise or key loss can permanently block governance recovery.

## Vulnerable pattern

- constructor seeds `admin`/`owner`/`upgrade_admin` storage
- privileged flows depend on that role
- no `set_*_admin`, `transfer_ownership`, `rotate_*`, or equivalent path

## Secure pattern

- provide explicit role rotation/revocation lifecycle
- gate role mutation with strong access control and eventing
- test key-loss/compromise recovery runbooks

## Detection

- constructor writes privileged address fields
- scan for absence of rotation primitives in ABI-exposed/admin methods

## False-positive caveats (Gate C / FP-10 evidence)

- immutable governance by design (must be explicitly documented and accepted)
- ownership lifecycle delegated to trusted component with verified hooks

## Minimum tests (PoC and regression targets)

- old admin loses privileges after rotation
- new admin gains expected privileges
- unauthorized caller cannot rotate privileged role
