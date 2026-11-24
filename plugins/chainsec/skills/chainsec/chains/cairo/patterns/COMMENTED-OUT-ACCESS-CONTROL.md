# COMMENTED-OUT-ACCESS-CONTROL

> **Detector class**: `COMMENTED_OUT_ACCESS_CONTROL`
> **Inject into**: Lens A (Access/State)
> **Category**: Access control
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-6
> **Module**: [modules/starknet-access-and-upgrades.md](../modules/starknet-access-and-upgrades.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Critical access checks are commented out while state-changing transfer paths remain active.

## Vulnerable pattern

- commented guard calls (`only_controller`, role checks, auth asserts)
- public function continues into transfer/mutation sink

## Secure pattern

- enforce live guard in executable path
- remove dead/testing bypass comments before release

## Detection

- commented access-control marker in sensitive function
- no equivalent live guard after stripping comments

## False-positive caveats (Gate C / FP-10 evidence)

- comments in dead code path that is never reachable/exposed

## Minimum tests (PoC and regression targets)

- unauthorized caller test must revert
- authorized caller happy-path test succeeds
