# UNSAFE-ADMIN-TRANSFER

> **Detector class**: `UNSAFE_ADMIN_TRANSFER`
> **Inject into**: Lens A (Access/State)
> **Category**: Access control
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-20, AV-122
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Admin transfer is single-step and unguarded, so a typo or malicious value can permanently lose privileged control.

## Vulnerable pattern

- `transfer_admin(new_admin)` writes admin directly
- no non-zero validation for `new_admin`
- no two-step accept/claim flow

## Secure pattern

- require non-zero `new_admin`
- use pending-admin + accept-admin two-step handover
- emit transition events for both schedule and accept

## Detection

- direct write to admin storage in `transfer_admin`
- absence of non-zero assertion and pending/accept surfaces

## False-positive caveats (Gate C / FP-10 evidence)

- deliberately immutable admin role in non-upgradeable/deprecated contracts with explicit governance controls

## Minimum tests (PoC and regression targets)

- zero admin transfer reverts
- pending admin must accept before role activation
- schedule and accept transitions emit admin-handover events
