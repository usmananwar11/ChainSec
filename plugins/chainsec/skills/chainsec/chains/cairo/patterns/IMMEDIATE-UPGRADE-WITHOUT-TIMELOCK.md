# IMMEDIATE-UPGRADE-WITHOUT-TIMELOCK

> **Detector class**: `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK`
> **Inject into**: Lens A (Access/State)
> **Category**: Upgrades
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-1, AV-13, AV-82
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Contract supports direct class-hash upgrade in a single privileged call (`upgrade`/`replace_class`) without a delay window.

## Vulnerable pattern

- `fn upgrade(...) { ... replace_class_syscall(...) }`
- no queued/scheduled upgrade state
- no minimum delay / timelock enforcement

## Secure pattern

- split into `schedule_upgrade` + `execute_upgrade`
- store pending class hash + scheduled timestamp
- enforce `now >= scheduled_at + upgrade_delay`

## Detection

- upgrade function performs `replace_class_syscall` or `upgradeable.upgrade`
- no timelock markers (`schedule_upgrade`, `upgrade_delay`, `pending_upgrade`, `timelock`)

## False-positive caveats (Gate C / FP-10 evidence)

- controlled environments may intentionally accept immediate upgrades
- external governance delays can exist off-chain (must be documented)

## Minimum tests (PoC and regression targets)

- cannot execute upgrade before delay
- can execute only after delay expires
- cancel path clears pending upgrade state
