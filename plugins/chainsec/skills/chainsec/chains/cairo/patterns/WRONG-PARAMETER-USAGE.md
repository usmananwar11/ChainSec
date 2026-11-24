# WRONG-PARAMETER-USAGE

> **Detector class**: `WRONG_PARAMETER_USAGE`
> **Inject into**: Lens B (Value flow)
> **Category**: Oracles / parameters
> **Related attack vectors** (heuristics.md, Extended heuristics): none
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Code assigns semantically distinct fields from the same parameter source, corrupting pricing/risk semantics.

## Vulnerable pattern

- constructs `{min, max}` (or similar pair) from the same max-only input
- ignores dedicated min/source parameter

## Secure pattern

- map each field from the intended parameter set
- assert `min <= max` and enforce spread policy

## Detection

- `min:` and `max:` both populated from `compacted_max_prices` (or equivalent)

## False-positive caveats (Gate C / FP-10 evidence)

- protocol intentionally uses fixed-price mode and documents `min == max`

## Minimum tests (PoC and regression targets)

- min/max source mapping tests
- spread/invariant tests for manipulated input packs
