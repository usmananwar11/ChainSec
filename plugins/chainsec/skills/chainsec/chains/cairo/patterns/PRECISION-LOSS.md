# PRECISION-LOSS

> **Detector class**: `PRECISION_LOSS`
> **Inject into**: Lens B (Value flow)
> **Category**: Math / precision
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-43, AV-53
> **Module**: [modules/felt252-arithmetic.md](../modules/felt252-arithmetic.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Percentage and vesting math is performed with an insufficient scale factor, causing material truncation and accounting drift.

## Vulnerable pattern

- helper uses low fixed scale (for example `SCALE_FACTOR = 100`)
- scaled division result is reused for value transfer or streaming calculations
- no invariant compensates for truncation over long durations

## Secure pattern

- use higher precision fixed-point math for time/price percentages
- round in a protocol-safe direction and document policy
- include invariants on cumulative streamed/withdrawn values

## Detection

- fixed small-scale constant used in division helpers
- helper output multiplied with token amounts and divided back by the same scale

## False-positive caveats (Gate C / FP-10 evidence)

- intentionally coarse precision with explicit product requirements and tests

## Minimum tests (PoC and regression targets)

- long-duration stream precision regression test
- cumulative withdrawn + refunded + remaining consistency check
