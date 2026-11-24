# MISSING-FEE-BOUNDS

> **Detector class**: `MISSING_FEE_BOUNDS`
> **Inject into**: Lens B (Value flow)
> **Category**: Fees / value flow
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-41
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Privileged runtime fee configuration accepts unbounded values, enabling DoS or abusive economics.

## Vulnerable pattern

- setter writes `new_fee` directly
- setter is privileged/admin-facing runtime configuration
- no max bound/guard in setter path
- downstream logic assumes bounded fee range

## Secure pattern

- enforce immutable upper bounds at setter edge
- validate per-asset fee updates against protocol constants

## Detection

- privileged fee setter with direct storage write
- no assertion comparing new fee to max basis points/constant

## Distinguish from `UNCHECKED-FEE-BOUND`

- `MISSING-FEE-BOUNDS`: runtime configuration setter paths (owner/admin controlled) missing bounds.
- `UNCHECKED-FEE-BOUND`: externally supplied fee-like values forwarded to deploy/storage/external calls without validation.

## False-positive caveats (Gate C / FP-10 evidence)

- fee bounds enforced in shared component called by setter

## Minimum tests (PoC and regression targets)

- out-of-range fee update reverts
- max-boundary fee update (`fee == MAX_FEE`) succeeds
- valid fee update preserves create/report flows
