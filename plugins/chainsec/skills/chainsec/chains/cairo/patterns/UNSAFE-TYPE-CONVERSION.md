# UNSAFE-TYPE-CONVERSION

> **Detector class**: `UNSAFE_TYPE_CONVERSION`
> **Inject into**: Lens D (Edge cases/Math)
> **Category**: Math / conversions
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-44, AV-169, AV-170
> **Module**: [modules/felt252-arithmetic.md](../modules/felt252-arithmetic.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Narrowing integer conversion can panic or truncate unexpectedly, causing DoS or logic corruption.

## Vulnerable pattern

- `u256` converted via `try_into::<u32/u64>()` in critical path
- conversion failure leads to `expect()` panic

## Secure pattern

- pre-validate bounds before narrowing
- use safe saturation/checked conversion policy with explicit error handling

## Detection

- `try_into().expect('u256 into u32 failed')` (or equivalent) in runtime checks

## False-positive caveats (Gate C / FP-10 evidence)

- conversion source is statically bounded by invariant and proven in tests/formal checks

## Minimum tests (PoC and regression targets)

- out-of-range conversion input reverts with controlled error
- in-range conversion path remains functional
