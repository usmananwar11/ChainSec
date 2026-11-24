# CEI-VIOLATION-ERC1155

> **Detector class**: `CEI_VIOLATION_ERC1155`
> **Inject into**: Lens C (External/Integration)
> **Category**: External calls / reentrancy
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-21, AV-33, AV-143
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Function performs ERC1155 `safe_transfer_from` (external interaction with callback surface)
before critical state updates, violating Check-Effects-Interactions ordering.

## Vulnerable pattern

- interaction: ERC1155 safe transfer
- effects: order/claim/status writes happen after transfer
- no reentrancy guard around callback-capable path

## Secure pattern

- apply effects before external interaction
- or enforce robust reentrancy guard around whole flow

## Detection

- function contains `safe_transfer_from`
- state mutation markers occur after transfer call
- no visible reentrancy lock/guard pattern

## False-positive caveats (Gate C / FP-10 evidence)

- callback target is provably trusted and non-reentrant (rare; must be documented)
- reentrancy is blocked by upstream global lock

## Minimum tests (PoC and regression targets)

- malicious callback contract cannot re-enter and double-process order
- state transition is committed before interaction or lock blocks recursion
