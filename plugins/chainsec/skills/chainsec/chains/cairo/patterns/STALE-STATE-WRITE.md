# STALE-STATE-WRITE

> **Detector class**: `STALE_STATE_WRITE`
> **Inject into**: Lens B (Value flow)
> **Category**: State updates
> **Related attack vectors** (heuristics.md, Extended heuristics): none
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

A state field is updated and then overwritten later in the same flow using stale pre-update values.

## Vulnerable pattern

- first write stores incremented/decremented value
- later conditional write reconstructs struct with old field value
- final state is inconsistent with transferred amounts

## Secure pattern

- derive second write from latest state snapshot
- avoid duplicating struct reconstruction across branches

## Detection

- same field written twice in a function
- second write references pre-update variable while branch condition uses post-update data

## False-positive caveats (Gate C / FP-10 evidence)

- explicit rollback/compensation logic where second write is intentional and tested

## Minimum tests (PoC and regression targets)

- post-withdraw consistency invariant for aggregate balances
- branch test covering depletion/finalization path
